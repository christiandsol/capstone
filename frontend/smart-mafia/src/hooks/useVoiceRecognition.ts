import { useRef, useState } from 'react';
import { VOICE_COMMANDS } from '../constants/voice-commands';

declare global {
    interface Window {
        webkitSpeechRecognition: any;
        SpeechRecognition: any;
    }
}

export const useVoiceRecognition = (
    onCommand: (code: number, phrase: string) => void
) => {
    const [isListening, setIsListening] = useState(false);
    const recognitionRef = useRef<any>(null);

    const start = () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            alert('Speech recognition not supported in this browser. Please use Chrome or Edge.');
            return;
        }

        if (!recognitionRef.current) {
            const recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            recognition.onstart = () => {
                setIsListening(true);
                console.log('[Voice] Listening started...');
            };

            recognition.onresult = (event: any) => {
                const last = event.results.length - 1;
                const text = event.results[last][0].transcript.toLowerCase();
                console.log('[Voice] Heard:', text);

                for (const [phrase, code] of Object.entries(VOICE_COMMANDS)) {
                    if (text.includes(phrase)) {
                        console.log(`[Voice] Command matched: "${phrase}" → Code: ${code}`);
                        onCommand(code, phrase);
                        break;
                    }
                }
            };

            recognition.onerror = (event: any) => {
                console.error('[Voice] Error:', event.error);
                if (event.error === 'no-speech') {
                    console.log('[Voice] No speech detected, still listening...');
                }
            };

            recognition.onend = () => {
                console.log('[Voice] Recognition ended');
                if (isListening) {
                    recognition.start();
                }
            };

            recognitionRef.current = recognition;
        }

        recognitionRef.current.start();
    };

    const stop = () => {
        setIsListening(false);
        recognitionRef.current?.stop();
        console.log('[Voice] Stopped listening');
    };

    return { isListening, start, stop };
};
