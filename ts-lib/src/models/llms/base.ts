import { Step, Message, Summary } from '../agent.js';
import { Tool } from '../tool.js';
import { LLM, LLMArgs } from '../session.js';

export interface ChatMessage {
  role: string;
  content: string;
}

export abstract class BaseLLM implements LLM {
  abstract callLLM(messages: ChatMessage[], responseFormat: any): Promise<any>;

  async get_output(args: LLMArgs): Promise<any> {
    const messages = this.getMessages(args);
    return this.callLLM(messages, args.responseFormat);
  }

  protected getMessages(args: LLMArgs): ChatMessage[] {
    const { currentStep, tools, history, systemMessage, persona } = args;
    const parts: string[] = [];
    if (systemMessage) parts.push(systemMessage);
    if (persona) parts.push(persona);
    parts.push(`Instructions: ${currentStep.description}`);
    if (currentStep.routes.length) {
      const routes = currentStep.routes
        .map((r) => `${r.target}: ${r.condition}`)
        .join('\n');
      parts.push(`Available Routes:\n${routes}`);
    }
    if (currentStep.available_tools.length) {
      const toolDesc = currentStep.available_tools
        .map((t) => tools[t])
        .filter(Boolean)
        .map((t) => `- ${t.name}: ${t.description}`)
        .join('\n');
      if (toolDesc) parts.push(`Available Tools:\n${toolDesc}`);
    }
    const sys = parts.join('\n');

    const hist = history
      .map((h) => {
        if ((h as Message).role) return `${(h as Message).role}: ${(h as Message).content}`;
        if ((h as Summary).summary) return `Summary: ${(h as Summary).summary.join(' ')}`;
        return `Step: ${(h as any).step_id}`;
      })
      .join('\n');

    return [
      { role: 'system', content: sys },
      { role: 'user', content: hist },
    ];
  }
}
