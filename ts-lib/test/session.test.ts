import { describe, it, expect } from 'vitest';
import { Step, createDecisionModel, Agent, Session, Tool } from '../src/index.js';
import { z } from 'zod';

class MockLLM {
  responses: any[] = [];
  received: any[] = [];
  setResponse(resp: any) {
    this.responses.push(resp);
  }
  get_output() {
    this.received.push(null);
    return this.responses.shift();
  }
}

describe('Agent and Session', () => {
  const start = new Step({
    step_id: 'start',
    description: 'begin',
    routes: [{ target: 'end', condition: 'done' }],
    available_tools: ['echo']
  });
  const end = new Step({ step_id: 'end', description: 'finish' });
  const echo = new Tool('echo', 'Echo', (args: { text: string }) => args.text, {
    text: { type: z.string() }
  });
  const steps = { start, end };

  it('runs a simple conversation', async () => {
    const llm = new MockLLM();
    const agent = new Agent({ name: 'a', llm, steps, startStepId: 'start', tools: [echo] });
    const session = agent.createSession();

    const model = createDecisionModel(start, [echo]);
    llm.setResponse({ reasoning: ['hi'], action: 'ASK', response: 'hello' });
    const [dec1] = await session.next();
    expect(model.parse(dec1)).toBeTruthy();
    expect(dec1.action).toBe('ASK');

    llm.setResponse({ reasoning: ['use'], action: 'TOOL_CALL', tool_call: { tool_name: 'echo', tool_kwargs: { text: 'bye' } } });
    const [dec2, res] = await session.next('run');
    expect(dec2.action).toBe('TOOL_CALL');
    expect(res).toBe('bye');
  });
});
