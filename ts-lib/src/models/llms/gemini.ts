import { GoogleGenerativeAI } from '@google/generative-ai';
import { BaseLLM, ChatMessage } from './base.js';

export interface GeminiOptions {
  apiKey: string;
  model?: string;
}

export class Gemini extends BaseLLM {
  modelName: string;
  model: any;

  constructor(options: GeminiOptions) {
    super();
    const { apiKey, model = 'gemini-pro' } = options;
    const client = new GoogleGenerativeAI(apiKey);
    this.modelName = model;
    this.model = client.getGenerativeModel({ model });
  }

  async callLLM(messages: ChatMessage[], _format: any): Promise<any> {
    const system = messages.find((m) => m.role === 'system')?.content ?? '';
    const user = messages.find((m) => m.role === 'user')?.content ?? '';
    const result = await this.model.generateContent({
      contents: [{ role: 'user', parts: [{ text: user }] }],
      systemInstruction: system,
      responseMimeType: 'application/json',
    });
    const text = result.response.text();
    return JSON.parse(text);
  }
}
