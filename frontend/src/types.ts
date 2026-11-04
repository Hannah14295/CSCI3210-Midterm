import { z } from 'zod';

export const userSchema = z.object({ id: z.number(), username: z.string() });
const decimalSchema = z.union([z.string(), z.number()]).transform(Number);
export const metricsSchema = z.object({
  typed_characters: z.number(), correct_characters: z.number(), correct_prefix: z.number(),
  progress: z.number(), accuracy: z.number(), complete: z.boolean(), wpm: z.number(),
});
export const participantSchema = z.object({
  id: z.number(), player: userSchema, joined_at: z.string(), revision: z.number(),
  metrics: metricsSchema, finished_at: z.string().nullable(),
  elapsed_seconds: decimalSchema.nullable(), wpm: decimalSchema.nullable(), accuracy: decimalSchema.nullable(),
});
export const raceSchema = z.object({
  id: z.number(), paragraph: z.number(), paragraph_text: z.string(), host: userSchema,
  status: z.enum(['waiting', 'running', 'finished']), created_at: z.string(),
  started_at: z.string().nullable(), participants: z.array(participantSchema),
});
export const paragraphSchema = z.object({ id: z.number(), title: z.string(), text: z.string() });
export const resultSchema = z.object({
  rank: z.number(), id: z.number(), race: z.number(), player: userSchema,
  wpm: decimalSchema, accuracy: decimalSchema.nullable(), elapsed_seconds: decimalSchema, finished_at: z.string(),
});
export const authSchema = z.object({ user: userSchema, token: z.string() });
export const pageSchema = <T extends z.ZodType>(item: T) => z.object({
  count: z.number(), next: z.string().nullable(), previous: z.string().nullable(), results: z.array(item),
});
export const socketEventSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('auth.required') }),
  z.object({ type: z.literal('connected'), race_id: z.number(), player: userSchema, race: raceSchema, your_text: z.string() }),
  z.object({ type: z.literal('race.updated'), race: raceSchema }),
  metricsSchema.extend({
    type: z.literal('progress.updated'), race_id: z.number(), player: userSchema, revision: z.number(),
    finished_at: z.string().nullable(), elapsed_seconds: z.number(),
  }),
  z.object({ type: z.literal('error'), detail: z.unknown(), status: z.number().optional() }),
]);
export type User = z.infer<typeof userSchema>;
export type Metrics = z.infer<typeof metricsSchema>;
export type Participant = z.infer<typeof participantSchema>;
export type Race = z.infer<typeof raceSchema>;
export type Paragraph = z.infer<typeof paragraphSchema>;
export type Result = z.infer<typeof resultSchema>;
