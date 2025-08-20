import { Step, Message, Summary } from './agent.js';
import { z } from 'zod';

export interface FlowContext {
  flow_id: string;
  entry_step: string;
  previous_context?: Array<Message | Summary>;
  metadata?: Record<string, any>;
}

export interface FlowComponent {
  enter(context: FlowContext): void;
  exit(context: FlowContext): any;
  cleanup(context: FlowContext): void;
}

export interface FlowConfig {
  flow_id: string;
  enters: string[];
  exits: string[];
  description?: string;
  components?: Record<string, Record<string, any>>;
}

export const FlowConfigSchema = z.object({
  flow_id: z.string(),
  enters: z.array(z.string()),
  exits: z.array(z.string()),
  description: z.string().optional(),
  components: z.record(z.record(z.any())).optional(),
});

export class Flow {
  config: FlowConfig;
  flow_id: string;
  entrySteps: Set<string>;
  exitSteps: Set<string>;
  steps: Record<string, Step>;
  components: Record<string, FlowComponent> = {};
  activeContexts: Record<string, FlowContext> = {};

  constructor(
    config: FlowConfig,
    steps: Step[],
    componentRegistry: Record<string, () => FlowComponent> = {},
  ) {
    this.config = config;
    this.flow_id = config.flow_id;
    this.entrySteps = new Set(config.enters);
    this.exitSteps = new Set(config.exits);
    this.steps = Object.fromEntries(steps.map((s) => [s.step_id, s]));
    const comps = config.components ?? {};
    for (const name of Object.keys(comps)) {
      if (componentRegistry[name]) {
        this.components[name] = componentRegistry[name]();
      }
    }
  }

  canEnter(stepId: string): boolean {
    return this.entrySteps.has(stepId);
  }
  canExit(stepId: string): boolean {
    return this.exitSteps.has(stepId);
  }
  containsStep(stepId: string): boolean {
    return stepId in this.steps;
  }

  enter(entryStep: string, previousContext?: Array<Message | Summary>, metadata: Record<string, any> = {}): FlowContext {
    if (!this.canEnter(entryStep)) {
      throw new Error(`Step '${entryStep}' is not a valid entry point for flow '${this.flow_id}'`);
    }
    const context: FlowContext = {
      flow_id: this.flow_id,
      entry_step: entryStep,
      previous_context: previousContext,
      metadata,
    };
    const key = `${this.flow_id}:${entryStep}`;
    this.activeContexts[key] = context;
    for (const comp of Object.values(this.components)) {
      comp.enter(context);
    }
    return context;
  }

  exit(exitStep: string, context: FlowContext): Record<string, any> {
    if (!this.canExit(exitStep)) {
      throw new Error(`Step '${exitStep}' is not a valid exit point for flow '${this.flow_id}'`);
    }
    const data: Record<string, any> = {};
    for (const [name, comp] of Object.entries(this.components)) {
      data[name] = comp.exit(context);
    }
    const key = `${context.flow_id}:${context.entry_step}`;
    delete this.activeContexts[key];
    return data;
  }

  cleanup(context: FlowContext): void {
    for (const comp of Object.values(this.components)) {
      comp.cleanup(context);
    }
    const key = `${context.flow_id}:${context.entry_step}`;
    delete this.activeContexts[key];
  }

  getComponent(name: string): FlowComponent | undefined {
    return this.components[name];
  }

  getMemory(): FlowComponent | undefined {
    return this.getComponent('memory');
  }
}

export class FlowManager {
  flows: Record<string, Flow> = {};
  stepToFlows: Record<string, string[]> = {};

  registerFlow(flow: Flow): void {
    this.flows[flow.flow_id] = flow;
    for (const step of Object.keys(flow.steps)) {
      if (!this.stepToFlows[step]) this.stepToFlows[step] = [];
      this.stepToFlows[step].push(flow.flow_id);
    }
  }

  getFlowsForStep(stepId: string): Flow[] {
    return (this.stepToFlows[stepId] || []).map((id) => this.flows[id]);
  }

  findEntryFlows(stepId: string): Flow[] {
    return Object.values(this.flows).filter((f) => f.canEnter(stepId));
  }
  findExitFlows(stepId: string): Flow[] {
    return Object.values(this.flows).filter((f) => f.canExit(stepId));
  }

  transitionBetweenFlows(fromFlow: Flow, toFlow: Flow, transitionStep: string, context: FlowContext): FlowContext {
    const exitData = fromFlow.exit(transitionStep, context);
    return toFlow.enter(transitionStep, context.previous_context, { ...context.metadata, previous_flow_data: exitData });
  }
}
