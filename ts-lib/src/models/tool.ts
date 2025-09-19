import { z } from 'zod';

export interface ToolParameter {
  type: z.ZodTypeAny;
  description?: string;
  default?: unknown;
}

export class Tool {
  name: string;
  description: string;
  fn: (...args: any[]) => any;
  parameters: Record<string, ToolParameter>;
  private _argsSchema?: z.ZodObject<any>;

  constructor(
    name: string,
    description: string,
    fn: (...args: any[]) => any,
    parameters: Record<string, ToolParameter> = {}
  ) {
    this.name = name;
    this.description = description;
    this.fn = fn;
    this.parameters = parameters;
  }

  static fromFunction(
    fn: (...args: any[]) => any,
    description?: string,
    params: Record<string, ToolParameter> = {}
  ) {
    return new Tool(fn.name, description ?? '', fn, params);
  }

  getArgsSchema(): z.ZodObject<any> {
    if (!this._argsSchema) {
      const shape: Record<string, z.ZodTypeAny> = {};
      for (const [key, param] of Object.entries(this.parameters)) {
        let schema = param.type;
        if (param.default !== undefined) {
          schema = schema.optional().default(param.default);
        }
        shape[key] = schema;
      }
      this._argsSchema = z.object(shape);
    }
    return this._argsSchema;
  }

  run(args: Record<string, unknown>): string {
    const validated = this.getArgsSchema().parse(args);
    return String(this.fn(validated));
  }
}
