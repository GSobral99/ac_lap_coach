import subprocess

def speak(messages):
    full_text = ". ".join(messages)
    full_text = full_text.replace('"', "'")
    command = f'Add-Type -AssemblyName System.Speech; ' \
              f'(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{full_text}")'
    subprocess.run(["powershell", "-Command", command])
    
if __name__ == "__main__":
    speak(["Primeira frase", "Segunda frase", "Terceira frase"])