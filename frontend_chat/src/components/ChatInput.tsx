import { useState } from 'react';
import { Mic, MicOff, Send } from 'lucide-react';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { api } from '../services/api';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

function ChatInput({ onSendMessage, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');
  const { isRecording, audioBlob, startRecording, stopRecording, clearRecording } = useAudioRecorder();
  const [isTranscribing, setIsTranscribing] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const handleVoiceToggle = async () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const handleTranscribe = async () => {
    if (audioBlob) {
      setIsTranscribing(true);
      try {
        const result = await api.transcribeAudio(audioBlob);
        setInput(result.text);
        clearRecording();
      } catch (error) {
        console.error('Transcription failed:', error);
      } finally {
        setIsTranscribing(false);
      }
    }
  };

  // Auto-transcribe when recording stops
  if (audioBlob && !isTranscribing) {
    handleTranscribe();
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <button
        type="button"
        className={`voice-button ${isRecording ? 'recording' : ''}`}
        onClick={handleVoiceToggle}
        disabled={disabled || isTranscribing}
        title={isRecording ? 'Stop recording' : 'Start voice input'}
      >
        {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
      </button>

      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={isTranscribing ? 'Transcribing...' : 'Ask me anything about EVE Online...'}
        disabled={disabled || isRecording || isTranscribing}
      />

      <button
        type="submit"
        className="send-button"
        disabled={!input.trim() || disabled}
        title="Send message"
      >
        <Send size={20} />
      </button>
    </form>
  );
}

export default ChatInput;
