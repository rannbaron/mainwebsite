#!/usr/bin/env python3
"""
Antigravity Desktop Voice Task Recorder
=======================================
Allows Rann to dictate tasks directly from the laptop microphone or terminal.
Uses `arecord` or `ffmpeg` to capture microphone audio and submits it to
the Antigravity voice task ingestion pipeline.
"""

import os
import sys
import subprocess
import signal
import tempfile
import argparse
from pathlib import Path

# Add backend directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from task_priority_backend import ingest_voice_task

def record_audio_arecord(output_path: str, duration: int = None) -> bool:
    """Records audio using arecord (standard ALSA recorder on Linux)."""
    cmd = ["arecord", "-f", "cd", "-t", "wav", "-q", output_path]
    if duration:
        cmd.extend(["-d", str(duration)])
    
    proc = subprocess.Popen(cmd)
    if duration:
        print(f"🎙️  Recording for {duration} seconds... Speak now!")
        proc.wait()
    else:
        print("🎙️  Recording from laptop microphone... Speak clearly!")
        print("    [Press ENTER when you are done speaking]")
        try:
            input()
        except KeyboardInterrupt:
            pass
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
    return os.path.exists(output_path) and os.path.getsize(output_path) > 1000

def record_audio_ffmpeg(output_path: str, duration: int = None) -> bool:
    """Fallback audio recorder using ffmpeg."""
    cmd = ["ffmpeg", "-y", "-f", "alsa", "-i", "default", "-ac", "1", "-ar", "16000", "-loglevel", "quiet"]
    if duration:
        cmd.extend(["-t", str(duration)])
    cmd.append(output_path)

    proc = subprocess.Popen(cmd)
    if duration:
        print(f"🎙️  Recording via ffmpeg for {duration} seconds... Speak now!")
        proc.wait()
    else:
        print("🎙️  Recording via ffmpeg... Speak clearly!")
        print("    [Press ENTER when you are done speaking]")
        try:
            input()
        except KeyboardInterrupt:
            pass
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
    return os.path.exists(output_path) and os.path.getsize(output_path) > 1000

def main():
    parser = argparse.ArgumentParser(description="Antigravity Desktop Voice Task Recorder")
    parser.add_argument("--duration", "-d", type=int, default=None, help="Record for a fixed number of seconds")
    parser.add_argument("--text", "-t", type=str, default=None, help="Directly ingest text without microphone recording")
    parser.add_argument("--priority", "-p", type=int, default=None, help="Explicit priority override (1 to 10)")
    parser.add_argument("--file", "-f", type=str, default=None, help="Ingest an existing audio file (.wav, .webm, .m4a)")
    args = parser.parse_args()

    print("=======================================================")
    print(" ANTIGRAVITY VOICE TASK INGESTION (DESKTOP / TERMINAL)")
    print("=======================================================")

    if args.text:
        print(f"Ingesting text: '{args.text}'")
        res = ingest_voice_task(audio_bytes=b"", explicit_text=args.text, explicit_priority=args.priority)
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"[Error] Audio file not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        audio_bytes = file_path.read_bytes()
        print(f"Ingesting audio file: {file_path.name} ({len(audio_bytes):,} bytes)")
        res = ingest_voice_task(audio_bytes=audio_bytes, filename=file_path.name, explicit_priority=args.priority)
    else:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_wav = tmp.name

        recorded = False
        # Try arecord first
        if subprocess.run(["which", "arecord"], capture_output=True).returncode == 0:
            try:
                recorded = record_audio_arecord(tmp_wav, duration=args.duration)
            except Exception as e:
                print(f"[Warning] arecord failed: {e}. Trying ffmpeg...")

        # Fallback to ffmpeg if arecord failed
        if not recorded and subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0:
            try:
                recorded = record_audio_ffmpeg(tmp_wav, duration=args.duration)
            except Exception as e:
                print(f"[Warning] ffmpeg recording failed: {e}")

        if not recorded:
            print("[Error] No audio could be captured from microphone.", file=sys.stderr)
            if os.path.exists(tmp_wav):
                os.unlink(tmp_wav)
            sys.exit(1)

        print(f"\nProcessing recorded audio ({os.path.getsize(tmp_wav):,} bytes)...")
        audio_bytes = Path(tmp_wav).read_bytes()
        res = ingest_voice_task(audio_bytes=audio_bytes, filename="mic_recording.wav", explicit_priority=args.priority)
        if os.path.exists(tmp_wav):
            os.unlink(tmp_wav)

    if res.get("status") == "success":
        task = res.get("task", {})
        print("\n✅ Task Successfully Ingested!")
        print(f"   • Transcription: \"{res.get('transcription')}\"")
        print(f"   • Task ID:       {task.get('id')}")
        print(f"   • Title:         {task.get('title')}")
        print(f"   • Priority:      P={task.get('priority')} ({task.get('priority_rationale')})")
        print(f"   • Domain Agent:  [{task.get('domain', '').upper()}]")
        print(f"   • Status:        {task.get('status', '').upper()}")
        if task.get("preempted_task"):
            pt = task["preempted_task"]
            print(f"   ⚡ PREEMPTION TRIGGERED: Paused Task #{pt.get('id')} '{pt.get('title')}' (P={pt.get('priority')})")
    else:
        print(f"\n❌ Ingestion Failed: {res.get('message')}")
        print(res)

if __name__ == "__main__":
    main()
