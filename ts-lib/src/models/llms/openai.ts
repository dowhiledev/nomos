import { OpenAI as Client, ClientOptions } from 'openai';
import type { ChatCompletionMessageParam } from 'openai/resources/chat/completions';
import { BaseLLM, ChatMessage } from './base.js';

export interface OpenAIOptions extends ClientOptions {
  model?: string;
}

export class OpenAI extends BaseLLM {
  client: Client;
  model: string;

  constructor(options: OpenAIOptions = {}) {
    super();
    const { model = 'gpt-3.5-turbo', ...opts } = options;
    this.model = model;
    this.client = new Client(opts);
  }

  async callLLM(messages: ChatMessage[], _format: any): Promise<any> {
    const resp = await this.client.chat.completions.create({
      model: this.model,
      messages: messages as ChatCompletionMessageParam[],
      response_format: { type: 'json_object' },
    });
    const content = resp.choices[0]?.message?.content ?? '{}';
    return JSON.parse(content);
  }
}
