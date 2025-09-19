import { describe, it, expect } from 'vitest';
import { Step } from '../src/models/agent.js';
import { Flow, FlowConfig, FlowManager } from '../src/index.js';

const steps = [
  new Step({ step_id: 's1', description: 'one' }),
  new Step({ step_id: 's2', description: 'two' }),
  new Step({ step_id: 's3', description: 'three' })
];

const config: FlowConfig = {
  flow_id: 'f1',
  enters: ['s1'],
  exits: ['s3'],
};

describe('Flow and FlowManager', () => {
  it('handles flow entry and exit', () => {
    const flow = new Flow(config, steps);
    const ctx = flow.enter('s1');
    expect(flow.activeContexts[`f1:s1`]).toBeTruthy();
    const data = flow.exit('s3', ctx);
    expect(data).toEqual({});
  });

  it('registers flows', () => {
    const fm = new FlowManager();
    const flow = new Flow(config, steps);
    fm.registerFlow(flow);
    expect(fm.getFlowsForStep('s1').length).toBe(1);
  });
});
