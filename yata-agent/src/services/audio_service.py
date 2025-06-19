from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Dict

from .audio_service_interface import AudioServiceInterface

# Whisper API が 0.1 秒未満を拒否するための最小長 (ms)
_MIN_DURATION_MS = 150  # 0.15 秒

class AudioService(AudioServiceInterface):
    """Handle heavy audio processing in a background thread using ffmpeg."""

    async def mix_and_export(
        self,
        sink_audio_data: Dict[int, SimpleNamespace],
        encoding: str,
        out_path: str,
    ) -> str:
        """Overlay user tracks and write to *out_path* using ffmpeg.

        The heavy ffmpeg work is executed in ``asyncio.to_thread`` so
        that the event-loop remains responsive.
        """

        def _work() -> str:
            if not sink_audio_data:
                raise ValueError("sink_audio_data is empty")

            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            out_path_ogg = Path(out_path).with_suffix(".ogg")

            # Save all audio files to temporary files
            temp_files = []
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                
                for i, (user_id, audio) in enumerate(sink_audio_data.items()):
                    temp_file = temp_dir_path / f"user_{user_id}.wav"
                    audio.file.seek(0)
                    with open(temp_file, 'wb') as f:
                        f.write(audio.file.read())
                    temp_files.append(temp_file)

                if len(temp_files) == 1:
                    # Single file - just convert to OGG with proper settings
                    cmd = [
                        'ffmpeg', '-y',
                        '-i', str(temp_files[0]),
                        '-ac', '1',  # mono
                        '-ar', '16000',  # 16kHz sample rate
                        '-c:a', 'libopus',
                        '-b:a', '12k',
                        '-application', 'voip',
                        str(out_path_ogg)
                    ]
                else:
                    # Multiple files - mix them
                    # Create filter_complex for mixing multiple audio streams
                    filter_inputs = []
                    for i in range(len(temp_files)):
                        filter_inputs.append(f'[{i}:a]')
                    
                    filter_complex = f"{''.join(filter_inputs)}amix=inputs={len(temp_files)}:duration=longest:dropout_transition=2[mixed]"
                    
                    cmd = ['ffmpeg', '-y']
                    for temp_file in temp_files:
                        cmd.extend(['-i', str(temp_file)])
                    
                    cmd.extend([
                        '-filter_complex', filter_complex,
                        '-map', '[mixed]',
                        '-ac', '1',  # mono
                        '-ar', '16000',  # 16kHz sample rate
                        '-c:a', 'libopus',
                        '-b:a', '12k',
                        '-application', 'voip',
                        str(out_path_ogg)
                    ])

                # Execute ffmpeg command
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f"ffmpeg failed: {e.stderr}") from e

                # Check if output file was created and has reasonable size
                if not out_path_ogg.exists():
                    raise RuntimeError("ffmpeg did not create output file")
                
                output_size = out_path_ogg.stat().st_size
                if output_size < 100:  # Very small file, probably empty
                    raise RuntimeError(f"Output file too small: {output_size} bytes")

                return str(out_path_ogg)

        return await asyncio.to_thread(_work) 