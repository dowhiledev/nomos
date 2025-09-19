import { describe, it, expect } from 'vitest';
import { Step } from '../src/models/agent.js';
import { Tool } from '../src/models/tool.js';
import { BaseLLM } from '../src/models/llms/base.js';
import { z } from 'zod';

class DummyLLM extends BaseLLM {
  async callLLM(msgs: any[], fmt: any): Promise<any> {
    return { msgs, fmt };
  }
}

describe('BaseLLM', () => {
  it('builds messages from session context', async () => {
    const step = new Step({
      step_id: 's1',
      description: 'say hi',
      routes: [{ target: 's2', condition: 'go' }],
      available_tools: ['echo'],
    });
    const tool = new Tool('echo', 'Echo', (args: { text: string }) => args.text, {
      text: { type: z.string() },
    });
    const llm = new DummyLLM();
    const res = await llm.get_output({
      steps: { s1: step, s2: step },
      currentStep: step,
      tools: { echo: tool },
      history: [{ role: 'user', content: 'hi' }],
      responseFormat: z.object({}),
      systemMessage: 'sys',
      persona: 'per',
    });
    expect(res.msgs[0].role).toBe('system');
    expect(res.msgs[1].role).toBe('user');
  });
});
