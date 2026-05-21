import os
import time
from microphone_input import MicrophoneRecorder
from pii_mask import IndianPIIAnonymizer
from transcriber import LocalTranscriber

# --- CONFIGURATION ---
RECORD_DURATION = 5        # How long to listen (seconds)
# ---------------------

def main():
    print("="*60)
    print("PRIVACY-PRESERVING VOICE ASSISTANT (SOFTWARE ONLY)")
    print("System Starting... (Loading AI Models)")
    print("="*60)

    # 1. Initialize Modules
    recorder = MicrophoneRecorder()
    
    print("1. Loading PII Filter...")
    anonymizer = IndianPIIAnonymizer(use_gliner=True)
    
    print("2. Loading Speech Engine (Small Model)...")
    transcriber = LocalTranscriber("small") 

    print("\n✅ SOFTWARE SYSTEM READY.")
    
    while True:
        try:
            print("\n" + "-"*40)
            cmd = input("Press ENTER to speak (or 'q' to quit): ")
            if cmd.lower() == 'q':
                break

            # 2. Record Audio
            filename = "command_buffer.wav"
            recorder.start_stream()
            recorder.record_audio(duration_seconds=RECORD_DURATION)
            recorder.save_recording(filename)
            recorder.stop_stream()

            # 3. Transcribe (Audio -> Text)
            print("🧠 Transcribing audio...")
            raw_text = transcriber.transcribe(filename)
            
            if not raw_text:
                print("⚠ No speech detected.")
                continue
                
            print(f"🗣  User said: '{raw_text}'")

            # 4. Privacy Filter (Text -> Safe Text)
            clean_result = anonymizer.anonymize_with_custom_operators(raw_text)
            safe_text = clean_result['anonymized']
            
            print(f"🛡  Sanitized Log: {safe_text}")
            
            # Highlight redactions for demo
            if clean_result['detected_entities']:
                removed_items = [f"{e['entity_type']}: {e['text']}" for e in clean_result['detected_entities']]
                print(f"   (Redacted: {', '.join(removed_items)})")

            # 5. Execute Logic (Mock Hardware Trigger)
            # The hardware team will insert their code here later.
            command_lower = raw_text.lower()
            
            if "light" in command_lower:
                if "on" in command_lower:
                    print("\n>>> HARDWARE TRIGGER: [LIGHT] -> [ON] <<<")
                elif "off" in command_lower:
                    print("\n>>> HARDWARE TRIGGER: [LIGHT] -> [OFF] <<<")
            
            elif "fan" in command_lower:
                 if "on" in command_lower:
                    print("\n>>> HARDWARE TRIGGER: [FAN] -> [ON] <<<")
                 elif "off" in command_lower:
                    print("\n>>> HARDWARE TRIGGER: [FAN] -> [OFF] <<<")
            
            else:
                print("ℹ General Command (No hardware trigger)")

            # Cleanup temp file
            if os.path.exists(filename):
                os.remove(filename)

        except KeyboardInterrupt:
            print("\nStopping system...")
            break
        except Exception as e:
            print(f"⚠ Unexpected System Error: {e}")

if __name__ == "__main__":
    main()