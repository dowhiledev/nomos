import fs from 'fs';
import yaml from 'js-yaml';
import { z } from 'zod';
import { Step, StepSchema } from './agent.js';
import { Agent } from './session.js';
import { FlowConfig, FlowConfigSchema } from './flow.js';
import type { LLM } from './session.js';
import type { Tool } from './tool.js';

export const AgentConfigSchema = z.object({
  name: z.string(),
  persona: z.string().optional(),
  steps: z.array(StepSchema),
  start_step_id: z.string(),
  system_message: z.string().optional(),
  show_steps_desc: z.boolean().optional(),
  max_errors: z.number().optional(),
  max_iter: z.number().optional(),
  flows: z.array(FlowConfigSchema).optional(),
});
export type AgentConfigData = z.infer<typeof AgentConfigSchema>;

export class AgentConfig {
  name: string;
  persona?: string;
  steps: Step[];
  start_step_id: string;
  system_message?: string;
  show_steps_desc?: boolean;
  max_errors: number;
  max_iter: number;
  flows?: FlowConfig[];

  constructor(data: AgentConfigData) {
    const parsed = AgentConfigSchema.parse(data);
    this.name = parsed.name;
    this.persona = parsed.persona;
    this.steps = parsed.steps.map((s) => new Step(s));
    this.start_step_id = parsed.start_step_id;
    this.system_message = parsed.system_message;
    this.show_steps_desc = parsed.show_steps_desc;
    this.max_errors = parsed.max_errors ?? 3;
    this.max_iter = parsed.max_iter ?? 5;
    this.flows = parsed.flows;
  }

  static fromYaml(path: string): AgentConfig {
    const content = fs.readFileSync(path, 'utf8');
    const data = yaml.load(content) as any;
    return new AgentConfig(data);
  }

  static fromYamlString(content: string): AgentConfig {
    const data = yaml.load(content) as any;
    return new AgentConfig(data);
  }

  toAgent(llm: LLM, tools: Tool[] = []): Agent {
    const stepMap: Record<string, Step> = {};
    for (const step of this.steps) {
      stepMap[step.step_id] = step;
    }
    return new Agent({
      name: this.name,
      llm,
      steps: stepMap,
      startStepId: this.start_step_id,
      persona: this.persona,
      systemMessage: this.system_message,
      tools,
      maxErrors: this.max_errors,
      maxIter: this.max_iter,
    });
  }
}
