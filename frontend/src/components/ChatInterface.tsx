import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import { useBOM } from '../context/BOMContext';

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) || '';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export const ChatInterface: React.FC = () => {
  const { items: bomItems } = useBOM();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I am your TripleT KiCad Agent. How can I help you with your electronics design today?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('handleSend fired! Input:', input);
    if (!input.trim() || isLoading) {
      console.log('handleSend aborted: input empty or already loading');
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    console.log('Adding user message to state:', userMessage);
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      console.log('Sending POST request to /api/chat...');
      
      // Inject BOM context if items exist
      const bomContextMessage = bomItems.length > 0 ? {
        role: "system",
        content: `Current BOM Context: The user has the following parts in their Bill of Materials: ${JSON.stringify(bomItems.map(i => ({ mpn: i.mpn, desc: i.description })))}. Use this context if they ask about 'my parts' or 'the BOM'.`
      } : null;

      const apiMessages: { role: string; content: string }[] = [...messages, userMessage].map(m => ({
        role: m.role,
        content: m.content
      }));

      if (bomContextMessage) {
        // Insert BOM context before the last user message
        apiMessages.splice(apiMessages.length - 1, 0, bomContextMessage);
      }

      const response = await axios.post(`${API_BASE}/api/chat`, {
        messages: apiMessages
      });
      console.log('Received response from backend:', response.data);

      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: response.data.content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error('Failed to send message error object:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}. Please check the console.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      console.log('handleSend completed.');
    }
  };

  return (
    <div className="flex flex-col h-[600px] w-full max-w-4xl mx-auto bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-blue-600 p-4 text-white flex items-center gap-2">
        <Bot className="h-6 w-6" />
        <h2 className="font-bold text-lg">KiCad AI Assistant</h2>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-lg flex gap-3 ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-white text-gray-800 shadow-sm border border-gray-200 rounded-bl-none'
              }`}
            >
              <div className="mt-1 flex-shrink-0">
                {m.role === 'user' ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5 text-blue-600" />}
              </div>
              <div className="text-sm whitespace-pre-wrap prose prose-sm max-w-none">
                <ReactMarkdown>{m.content}</ReactMarkdown>
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white text-gray-800 shadow-sm border border-gray-200 p-3 rounded-lg rounded-bl-none flex gap-2 items-center">
              <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
              <span className="text-sm italic text-gray-500">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSend} className="p-4 bg-white border-t border-gray-200 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask me to design a circuit or find a part..."
          className="flex-1 p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          <Send className="h-5 w-5" />
        </button>
      </form>
    </div>
  );
};
