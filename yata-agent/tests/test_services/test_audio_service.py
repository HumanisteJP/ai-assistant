import io
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

from services.audio_service import AudioService


@pytest.mark.asyncio
async def test_mix_and_export_creates_file(tmp_path):
    # Create a minimal valid WAV file header for testing
    wav_header = (
        b'RIFF'     # RIFF identifier
        b'\x2c\x00\x00\x00'  # File size (44 bytes - 8)
        b'WAVE'     # WAVE identifier
        b'fmt '     # Format chunk identifier
        b'\x10\x00\x00\x00'  # Format chunk size (16)
        b'\x01\x00'  # Audio format (PCM)
        b'\x01\x00'  # Number of channels (mono)
        b'\x40\x1f\x00\x00'  # Sample rate (8000 Hz)
        b'\x80\x3e\x00\x00'  # Byte rate
        b'\x02\x00'  # Block align
        b'\x10\x00'  # Bits per sample (16)
        b'data'     # Data chunk identifier
        b'\x08\x00\x00\x00'  # Data chunk size (8 bytes)
        b'\x00\x00\x01\x00\x02\x00\x03\x00'  # Sample audio data
    )

    sink_data = {
        1: SimpleNamespace(file=io.BytesIO(wav_header)),
    }
    out = tmp_path / "mix.wav"

    # Mock subprocess.run and Path.stat to simulate successful ffmpeg execution
    with patch("services.audio_service.subprocess.run") as mock_run, \
         patch("services.audio_service.Path") as mock_path:
        
        # Configure mock to simulate successful ffmpeg run
        mock_run.return_value = MagicMock(returncode=0)
        
        # Mock the output file path operations
        mock_output_path = MagicMock()
        mock_output_path.exists.return_value = True
        mock_output_path.stat.return_value.st_size = 1024  # Reasonable file size
        mock_output_path.__str__ = lambda self: str(tmp_path / "mix.ogg")
        
        # Configure Path mock to return our mock when with_suffix is called
        mock_path.return_value.parent.mkdir = MagicMock()
        mock_path.return_value.with_suffix.return_value = mock_output_path
        
        svc = AudioService()
        result = await svc.mix_and_export(sink_data, "wav", out.as_posix())

        # Assert
        mock_run.assert_called_once()
        assert result.endswith(".ogg")
        
        # Verify ffmpeg was called with correct parameters
        call_args = mock_run.call_args[0][0]  # First positional argument (command list)
        assert "ffmpeg" in call_args
        assert "-i" in call_args
        assert "-ac" in call_args and "1" in call_args  # mono
        assert "-ar" in call_args and "16000" in call_args  # 16kHz


@pytest.mark.asyncio
async def test_mix_and_export_multiple_users(tmp_path):
    # Test mixing multiple users' audio streams
    wav_header = (
        b'RIFF\x2c\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00'
        b'\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data\x08\x00\x00\x00'
        b'\x00\x00\x01\x00\x02\x00\x03\x00'
    )

    # Create separate BytesIO objects for each user
    audio1 = io.BytesIO(wav_header)
    audio1.seek(0)
    audio2 = io.BytesIO(wav_header)
    audio2.seek(0)

    # Multiple users (user IDs 12345 and 67890)
    sink_data = {
        12345: SimpleNamespace(file=audio1),
        67890: SimpleNamespace(file=audio2),
    }
    out = tmp_path / "mix.wav"

    # Mock subprocess.run, Path operations, and tempfile operations
    with patch("services.audio_service.subprocess.run") as mock_run, \
         patch("services.audio_service.Path") as mock_path_class, \
         patch("services.audio_service.tempfile.TemporaryDirectory") as mock_temp_dir:
        
        # Configure mock to simulate successful ffmpeg run
        mock_run.return_value = MagicMock(returncode=0)
        
        # Mock the output file path operations
        mock_output_path = MagicMock()
        mock_output_path.exists.return_value = True
        mock_output_path.stat.return_value.st_size = 2048  # Larger file for mixed audio
        mock_output_path.__str__ = lambda self: str(tmp_path / "mix.ogg")
        
        # Configure Path mock to return our mock when with_suffix is called
        mock_path_instance = MagicMock()
        mock_path_instance.parent.mkdir = MagicMock()
        mock_path_instance.with_suffix.return_value = mock_output_path
        mock_path_class.return_value = mock_path_instance
        
        # Mock the temporary directory
        mock_temp_context = MagicMock()
        mock_temp_dir.return_value.__enter__.return_value = str(tmp_path / "temp")
        mock_temp_dir.return_value.__exit__.return_value = None
        
        # Mock the file writing operations
        mock_open = MagicMock()
        with patch("builtins.open", mock_open):
            svc = AudioService()
            result = await svc.mix_and_export(sink_data, "wav", out.as_posix())

        # Assert
        mock_run.assert_called_once()
        assert result.endswith(".ogg")
        
        # Verify ffmpeg was called with multiple input files and amix filter
        call_args = mock_run.call_args[0][0]  # First positional argument (command list)
        assert "ffmpeg" in call_args
        assert call_args.count("-i") == 2  # Two input files
        assert "-filter_complex" in call_args
        
        # Find the filter_complex argument and verify it contains amix
        filter_idx = call_args.index("-filter_complex") + 1
        filter_complex = call_args[filter_idx]
        assert "amix" in filter_complex
        assert "inputs=2" in filter_complex  # Should mix 2 inputs
        assert "[mixed]" in filter_complex


@pytest.mark.asyncio
async def test_mix_and_export_handles_ffmpeg_error(tmp_path):
    # Arrange
    wav_header = (
        b'RIFF\x2c\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00'
        b'\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data\x08\x00\x00\x00'
        b'\x00\x00\x01\x00\x02\x00\x03\x00'
    )

    sink_data = {
        1: SimpleNamespace(file=io.BytesIO(wav_header)),
    }
    out = tmp_path / "mix.wav"

    # Mock subprocess.run to simulate ffmpeg failure
    with patch("services.audio_service.subprocess.run") as mock_run:
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, "ffmpeg", stderr="ffmpeg error")
        
        svc = AudioService()
        
        # Assert that RuntimeError is raised when ffmpeg fails
        with pytest.raises(RuntimeError, match="ffmpeg failed"):
            await svc.mix_and_export(sink_data, "wav", out.as_posix())


@pytest.mark.asyncio
async def test_mix_and_export_empty_data_raises_error():
    # Test that empty sink_audio_data raises ValueError
    svc = AudioService()
    
    with pytest.raises(ValueError, match="sink_audio_data is empty"):
        await svc.mix_and_export({}, "wav", "output.wav") 