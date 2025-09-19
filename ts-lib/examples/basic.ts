import { Step, Agent, Tool, OpenAI } from '../src/index.ts';
import { z } from 'zod';

const start = new Step({
  step_id: 'start',
  description: 'Say hello to the user',
  routes: [{ target: 'end', condition: 'user says bye' }],
  available_tools: ['echo']
});

const end = new Step({
  step_id: 'end',
  description: 'End of conversation',
  auto_flow: true
});

const echo = new Tool('echo', 'Repeat back provided text', (args: { text: string }) => args.text, {
  text: { type: z.string() }
});

const apiKey = process.env.OPENAI_API_KEY;
if (!apiKey) {
  console.error('OPENAI_API_KEY not set. Example cannot run.');
  process.exit(1);
}

const llm = new OpenAI({ apiKey });
const agent = new Agent({
  name: 'demo',
  llm,
  steps: { start, end },
  startStepId: 'start',
  tools: [echo]
});

(async () => {
  const session = agent.createSession();
  const [decision] = await session.next('Hello!');
  console.log('Decision:', decision);
})().catch((err) => {
  console.error('Example failed:', err);
});
