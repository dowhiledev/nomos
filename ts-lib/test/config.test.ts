import { describe, it, expect } from 'vitest';
import { AgentConfig } from '../src/models/config.js';
import { Step } from '../src/models/agent.js';
import { Tool } from '../src/models/tool.js';
import { z } from 'zod';

const yaml = `
name: test-agent
persona: helper
steps:
  - step_id: start
    description: Start here
  - step_id: end
    description: Finish
start_step_id: start
max_errors: 2
max_iter: 4
`;

describe('AgentConfig.fromYamlString', () => {
  it('parses yaml and creates Agent', () => {
    const cfg = AgentConfig.fromYamlString(yaml);
    expect(cfg.name).toBe('test-agent');
    expect(cfg.steps.length).toBe(2);
    const dummyLLM = { get_output: () => ({}) } as any;
    const agent = cfg.toAgent(dummyLLM, []);
    expect(agent.name).toBe('test-agent');
    expect(agent.maxErrors).toBe(2);
    expect(agent.maxIter).toBe(4);
    expect(agent.startStepId).toBe('start');
    expect(agent.steps['end']).toBeInstanceOf(Step);
  });
});
