import speech_recognition as sr
import time
# List of commands

#voice commands needed: after discussion, "ready to vote" -> gesture recognition
#
COMMANDS = ["assign players", "ready to start","ready to vote", "night time"]
WAKE_WORD = "okay mafia"
WAKE_WORD_ALTERNATIVES = ["okay mafia", "ok mafia", "okay maffia", "okay maphy", "ok maphy", "okay maf", "okay maff", "open maff", "open maf", "open mafia", "mafia", "maffia"]

def listen_for_okay_mafia():
    r = sr.Recognizer()
    
    r.energy_threshold = 200
    r.dynamic_energy_threshold = False
    
    consecutive_errors = 0
    max_consecutive_errors = 5  # More lenient

    with sr.Microphone() as source:
        print(f"Energy threshold set to: {r.energy_threshold}")
        print("Now listening for 'okay mafia'...\n")
        
        while True:
            try:
                # Wait for speech
                print("👂 Waiting for speech...", end=' ', flush=True)
                audio = r.listen(source, timeout=None, phrase_time_limit=3)
                print("✓ Got audio, processing...")
                
                result = r.recognize_google(audio, show_all=True)
                
                if not result or 'alternative' not in result:
                    print("   → No transcription available\n")
                    continue
                
                # PRINT ALL ALTERNATIVES
                print("   === Alternatives ===")
                for i, alternative in enumerate(result['alternative'], 1):
                    text = alternative['transcript']
                    confidence = alternative.get('confidence', 'N/A')
                    print(f"   {i}. '{text}' (confidence: {confidence})")
                print("   ====================\n")
                
                # Check for wake word
                for alternative in result['alternative']:
                    text = alternative['transcript'].lower()
                    
                    for wake_variant in WAKE_WORD_ALTERNATIVES:
                        if wake_variant in text:
                            print(f"WAKE WORD DETECTED: '{wake_variant}'")
                            print("=" * 50)
                            return True
                
                consecutive_errors = 0
                
            except sr.WaitTimeoutError:
                continue
                
            except sr.UnknownValueError:
                print("   → Could not understand audio\n")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print("Many unclear segments. Continuing anyway...\n")
                    consecutive_errors = 0
                continue
                
            except sr.RequestError as e:
                print(f"API error: {e}")
                print("Waiting 5 seconds before retrying...")
                time.sleep(5)
                continue
            
            except KeyboardInterrupt:
                print("\nStopping...")
                return False



def listen_for_command():
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True

    with sr.Microphone() as source:
        print("Now listening for a command (3 seconds)...")
        audio = r.record(source, duration=3)
        try:
            result = r.recognize_google(audio, show_all=True)
            

            #=====testing=====
            print("\n=== All alternatives ===")
            for i, alternative in enumerate(result['alternative'], 1):
                text = alternative['transcript']
                confidence = alternative.get('confidence', 'N/A')
                print(f"{i}. '{text}' (confidence: {confidence})")
            print("========================\n")   
            #=====testing=====
                         
            for alternative in result['alternative']:
                text = alternative['transcript'].lower()
                
                # Check if any command matches this alternative
                for cmd in COMMANDS:
                    if cmd in text:
                        print("Command recognized:", cmd)
                        return cmd
            return None
        except sr.UnknownValueError:
            print("Could not understand audio.")
            return None
        except sr.RequestError:
            print("API unavailable or network error.")
            return None
   
if __name__ == "__main__":
    listen_for_okay_mafia()  #listening for "okay mafia"
    command = listen_for_command()  # listen for command once awoken
    print("Final result:", command)
