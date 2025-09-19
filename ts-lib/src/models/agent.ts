import { z } from 'zod';
import type { Tool } from './tool';

export const RouteSchema = z.object({
  target: z.string(),
  condition: z.string(),
});
export type Route = z.infer<typeof RouteSchema>;

export const StepSchema = z.object({
  step_id: z.string(),
  description: z.string(),
  routes: z.array(RouteSchema).default([]),
  available_tools: z.array(z.string()).default([]),
  answer_model: z.any().optional(),
  auto_flow: z.boolean().default(false),
  quick_suggestions: z.boolean().default(false),
  flow_id: z.string().optional().nullable(),
});
export type StepData = z.infer<typeof StepSchema>;

export class Step {
  step_id: string;
  description: string;
  routes: Route[];
  available_tools: string[];
  answer_model?: unknown;
  auto_flow: boolean;
  quick_suggestions: boolean;
  flow_id?: string | null;

  constructor(data: StepData) {
    const parsed = StepSchema.parse(data);
    this.step_id = parsed.step_id;
    this.description = parsed.description;
    this.routes = parsed.routes;
    this.available_tools = parsed.available_tools;
    this.answer_model = parsed.answer_model;
    this.auto_flow = parsed.auto_flow;
    this.quick_suggestions = parsed.quick_suggestions;
    this.flow_id = parsed.flow_id;
    if (this.auto_flow && this.routes.length === 0 && this.available_tools.length === 0) {
      throw new Error(
        `Step '${this.step_id}': When auto_flow is true, at least one tool or route must be available`
      );
    }
    if (this.auto_flow && this.quick_suggestions) {
      throw new Error(
        `Step '${this.step_id}': When auto_flow is true, quick_suggestions cannot be true`
      );
    }
  }

  getAvailableRoutes(): string[] {
    return this.routes.map((r) => r.target);
  }

  toString(): string {
    return `[Step] ${this.step_id}: ${this.description}`;
  }
}

export const MessageSchema = z.object({
  role: z.string(),
  content: z.string(),
});
export type Message = z.infer<typeof MessageSchema>;

export const SummarySchema = z.object({
  summary: z.array(z.string()),
});
export type Summary = z.infer<typeof SummarySchema>;

export function createDecisionModel(currentStep: Step, currentStepTools: Tool[]) {
  const availableStepIds = currentStep.getAvailableRoutes();
  const toolIds = currentStepTools.map((t) => t.name);
  const actions = [
    ...(currentStep.auto_flow ? ['END'] : ['ASK', 'ANSWER', 'END']),
    ...(availableStepIds.length ? ['MOVE'] : []),
    ...(toolIds.length ? ['TOOL_CALL'] : []),
  ];
  const ActionEnum = z.enum(actions as [string, ...string[]]);

  const base: Record<string, z.ZodTypeAny> = {
    reasoning: z.array(z.string()),
    action: ActionEnum,
  };

  if (!currentStep.auto_flow) {
    base.response = z.optional(z.any());
    if (currentStep.quick_suggestions) {
      base.suggestions = z.array(z.string()).optional();
    }
  }
  if (availableStepIds.length) {
    base.step_transition = z.enum(availableStepIds as [string, ...string[]]).optional();
  }
  if (toolIds.length) {
    base.tool_call = z
      .object({
        tool_name: z.enum(toolIds as [string, ...string[]]),
        tool_kwargs: z.record(z.any()),
      })
      .optional();
  }

  return z.object(base);
}
