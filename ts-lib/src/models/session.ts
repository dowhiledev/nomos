import { z } from 'zod';
import { Step, Message, Summary, createDecisionModel } from './agent.js';
import { Tool } from './tool.js';

export interface StepIdentifier { step_id: string }

export interface LLMArgs {
  steps: Record<string, Step>;
  currentStep: Step;
  tools: Record<string, Tool>;
  history: Array<Message | StepIdentifier | Summary>;
  responseFormat: z.ZodTypeAny;
  systemMessage?: string;
  persona?: string;
}

export interface LLM {
  get_output(args: LLMArgs): Promise<any> | any;
}

export class Session {
  name: string;
  llm: LLM;
  steps: Record<string, Step>;
  currentStep: Step;
  startStepId: string;
  systemMessage?: string;
  persona?: string;
  tools: Record<string, Tool>;
  memory: Array<Message | StepIdentifier | Summary> = [];
  maxErrors: number;
  maxIter: number;

  constructor(options: {
    name: string;
    llm: LLM;
    steps: Record<string, Step>;
    startStepId: string;
    systemMessage?: string;
    persona?: string;
    tools?: Tool[];
    maxErrors?: number;
    maxIter?: number;
  }) {
    this.name = options.name;
    this.llm = options.llm;
    this.steps = options.steps;
    this.startStepId = options.startStepId;
    this.systemMessage = options.systemMessage;
    this.persona = options.persona;
    this.maxErrors = options.maxErrors ?? 3;
    this.maxIter = options.maxIter ?? 5;
    this.currentStep = this.steps[this.startStepId];
    const toolMap: Record<string, Tool> = {};
    for (const tool of options.tools ?? []) {
      toolMap[tool.name] = tool;
    }
    this.tools = toolMap;
  }

  private _runTool(toolName: string, kwargs: Record<string, unknown>): string {
    const tool = this.tools[toolName];
    if (!tool) {
      throw new Error(`Tool ${toolName} not found`);
    }
    return tool.run(kwargs);
  }

  private _getCurrentStepTools(): Tool[] {
    const list: Tool[] = [];
    for (const id of this.currentStep.available_tools) {
      const t = this.tools[id];
      if (t) list.push(t);
    }
    return list;
  }

  private async _getNextDecision(): Promise<any> {
    const model = createDecisionModel(this.currentStep, this._getCurrentStepTools());
    const response = await this.llm.get_output({
      steps: this.steps,
      currentStep: this.currentStep,
      tools: this.tools,
      history: this.memory,
      responseFormat: model,
      systemMessage: this.systemMessage,
      persona: this.persona,
    });
    return model.parse(response);
  }

  async next(userInput?: string, noErrors = 0, nextCount = 0): Promise<[any, any?]> {
    if (noErrors >= this.maxErrors) {
      throw new Error('Maximum errors reached');
    }
    if (nextCount >= this.maxIter) {
      throw new Error('Maximum iterations reached');
    }

    if (userInput) {
      this.memory.push({ role: 'user', content: userInput });
    }

    const decision = await this._getNextDecision();
    this.memory.push({ step_id: this.currentStep.step_id } as StepIdentifier);

    let toolResult: any = undefined;
    if (decision.action === 'ASK' || decision.action === 'ANSWER') {
      if (decision.response) {
        this.memory.push({ role: this.name, content: String(decision.response) });
      }
    } else if (decision.action === 'TOOL_CALL') {
      try {
        toolResult = this._runTool(decision.tool_call.tool_name, decision.tool_call.tool_kwargs);
        this.memory.push({ role: 'tool', content: String(toolResult) });
      } catch (e) {
        this.memory.push({ role: 'error', content: String(e) });
        return this.next(undefined, noErrors + 1, nextCount + 1);
      }
    } else if (decision.action === 'MOVE') {
      const target = decision.step_transition;
      if (target && this.steps[target]) {
        this.currentStep = this.steps[target];
      } else {
        this.memory.push({ role: 'error', content: `Invalid route: ${target}` });
        return this.next(undefined, noErrors + 1, nextCount + 1);
      }
    }

    return [decision, toolResult];
  }
}

export class Agent {
  name: string;
  llm: LLM;
  steps: Record<string, Step>;
  startStepId: string;
  persona?: string;
  systemMessage?: string;
  tools: Tool[];
  maxErrors: number;
  maxIter: number;

  constructor(options: {
    name: string;
    llm: LLM;
    steps: Record<string, Step>;
    startStepId: string;
    persona?: string;
    systemMessage?: string;
    tools?: Tool[];
    maxErrors?: number;
    maxIter?: number;
  }) {
    this.name = options.name;
    this.llm = options.llm;
    this.steps = options.steps;
    this.startStepId = options.startStepId;
    this.persona = options.persona;
    this.systemMessage = options.systemMessage;
    this.tools = options.tools ?? [];
    this.maxErrors = options.maxErrors ?? 3;
    this.maxIter = options.maxIter ?? 5;
  }

  createSession(): Session {
    return new Session({
      name: this.name,
      llm: this.llm,
      steps: this.steps,
      startStepId: this.startStepId,
      systemMessage: this.systemMessage,
      persona: this.persona,
      tools: this.tools,
      maxErrors: this.maxErrors,
      maxIter: this.maxIter,
    });
  }
}
