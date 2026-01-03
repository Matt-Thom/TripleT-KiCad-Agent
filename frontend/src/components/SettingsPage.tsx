import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Save } from 'lucide-react';

interface SettingsData {
    openai_api_key: string;
    anthropic_api_key: string;
    gemini_api_key: string;
    default_model: string;
}

export const SettingsPage: React.FC = () => {
    const [settings, setSettings] = useState<SettingsData>({
        openai_api_key: '',
        anthropic_api_key: '',
        gemini_api_key: '',
        default_model: 'gemini/gemini-pro'
    });
    const [status, setStatus] = useState('');

    useEffect(() => {
        const fetchSettings = async () => {
            try {
                const response = await axios.get('http://localhost:8000/api/settings');
                // Ensure no nulls are set to inputs
                const data = response.data;
                setSettings({
                    openai_api_key: data.openai_api_key || '',
                    anthropic_api_key: data.anthropic_api_key || '',
                    gemini_api_key: data.gemini_api_key || '',
                    default_model: data.default_model || 'gemini/gemini-pro'
                });
            } catch (error) {
                console.error("Failed to load settings", error);
            }
        };
        fetchSettings();
    }, []);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        setSettings({ ...settings, [e.target.name]: e.target.value });
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus('Saving...');
        try {
            await axios.post('http://localhost:8000/api/settings', settings);
            setStatus('Settings saved successfully!');
            setTimeout(() => setStatus(''), 3000);
        } catch (error) {
            console.error("Failed to save settings", error);
            setStatus('Failed to save settings.');
        }
    };

    return (
        <div className="p-6 max-w-2xl mx-auto bg-white rounded-lg shadow border border-gray-200 text-gray-800">
            <h2 className="text-2xl font-bold mb-6">Settings</h2>
            
            <form onSubmit={handleSave} className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700">Default AI Model</label>
                    <select
                        name="default_model"
                        value={settings.default_model}
                        onChange={handleChange}
                        className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    >
                        <optgroup label="Google Gemini (Frontier)">
                            <option value="gemini/gemini-3-pro">Gemini 3 Pro (Deep Think)</option>
                            <option value="gemini/gemini-3-flash">Gemini 3 Flash (High Speed)</option>
                            <option value="gemini/gemini-2.0-pro-exp">Gemini 2.0 Pro (Stable)</option>
                        </optgroup>
                        <optgroup label="OpenAI GPT">
                            <option value="gpt-5.2">GPT-5.2 (Agentic)</option>
                            <option value="gpt-4.1">GPT-4.1 (Coding Specialist)</option>
                            <option value="o1">o1 (High Reasoning)</option>
                        </optgroup>
                        <optgroup label="Anthropic Claude">
                            <option value="claude-4.5-opus">Claude 4.5 Opus (MCP Native)</option>
                            <option value="claude-3-5-sonnet-latest">Claude 3.5 Sonnet</option>
                        </optgroup>
                        <optgroup label="xAI Grok">
                            <option value="grok-4.1">Grok 4.1 (Tool Expert)</option>
                        </optgroup>
                    </select>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700">OpenAI API Key</label>
                    <input
                        type="password"
                        name="openai_api_key"
                        value={settings.openai_api_key}
                        onChange={handleChange}
                        placeholder="sk-..."
                        className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700">Anthropic API Key</label>
                    <input
                        type="password"
                        name="anthropic_api_key"
                        value={settings.anthropic_api_key}
                        onChange={handleChange}
                        placeholder="sk-ant-..."
                        className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700">Google Gemini API Key</label>
                    <input
                        type="password"
                        name="gemini_api_key"
                        value={settings.gemini_api_key}
                        onChange={handleChange}
                        placeholder="AIza..."
                        className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>

                <div className="pt-4">
                    <button
                        type="submit"
                        className="w-full bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 flex justify-center items-center gap-2"
                    >
                        <Save className="h-4 w-4" />
                        Save Settings
                    </button>
                </div>

                {status && (
                    <div className={`mt-2 text-center text-sm ${status.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>
                        {status}
                    </div>
                )}
            </form>
        </div>
    );
};
