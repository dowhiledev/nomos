import { describe, it, expect } from 'vitest';
import { Step, Route, createDecisionModel } from '../src/index.js';
import { Tool } from '../src/models/tool.js';
import { z } from 'zod';

describe('Step', () => {
  it('initializes with routes and tools', () => {
    const step = new Step({
      step_id: 'start',
      description: 'first',
      routes: [{ target: 'next', condition: 'go' }],
      available_tools: ['echo']
    });
    expect(step.step_id).toBe('start');
    expect(step.getAvailableRoutes()).toEqual(['next']);
  });

  it('auto_flow requires route or tool', () => {
    expect(
      () => new Step({ step_id: 'bad', description: 'bad', auto_flow: true })
    ).toThrow();
  });
});

describe('Tool', () => {
  it('runs with validated args', () => {
    const tool = new Tool('sum', 'add', ({ a, b }: { a: number; b: number }) => a + b, {
      a: { type: z.number() },
      b: { type: z.number() }
    });
    expect(tool.run({ a: 1, b: 2 })).toBe('3');
  });
});

describe('createDecisionModel', () => {
  it('builds schema using step and tool info', () => {
    const step = new Step({
      step_id: 'start',
      description: 'desc',
      routes: [{ target: 'end', condition: 'done' }],
      available_tools: ['echo']
    });
    const tool = new Tool('echo', 'Echo', (args: { text: string }) => args.text, {
      text: { type: z.string() }
    });
    const schema = createDecisionModel(step, [tool]);
    const result = schema.parse({
      reasoning: ['x'],
      action: 'MOVE',
      step_transition: 'end'
    });
    expect(result.step_transition).toBe('end');
  });
});
