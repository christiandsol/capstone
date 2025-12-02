import speech_recognition as sr

# List of commands

#voice commands needed: after discussion, "ready to vote" -> gesture recognition
#
COMMANDS = ["assign roles", "ready to vote", "the sun has set"]
WAKE_WORD = "okay mafia"

def listen_for_okay_mafia():
    r = sr.Recognizer()
    r.energy_threshold = 300 #can tune this
    r.dynamic_energy_threshold = True

    with sr.Microphone() as source:
        while True:
            print("Listening for okay mafia...")
            audio = r.record(source, duration=3)
            try:
                text = r.recognize_google(audio).lower()
                print("Heard:", text)
                if WAKE_WORD in text:
                    print("Okay mafia detected!")
                    return
            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                print("API unavailable or network error.")
                break

def listen_for_command():
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True

    with sr.Microphone() as source:
        print("Now listening for a command (5 seconds)...")
        audio = r.record(source, duration=5)
        try:
            text = r.recognize_google(audio).lower()
            print("You said:", text)
            for cmd in COMMANDS:
                if cmd in text:
                    print("Command recognized:", cmd)
                    return cmd
            print("No valid command detected.")
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
