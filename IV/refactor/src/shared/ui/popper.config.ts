export interface PopperModifier {
  readonly name: string;
  readonly options?: Readonly<Record<string, unknown>>;
}

export interface PopperOptions {
  readonly modifiers?: readonly PopperModifier[];
}

const ARROW_PADDING = { left: 14, right: 13, top: 6, bottom: 6 } as const;

export const withArrowModifier = (options: PopperOptions): PopperOptions => ({
  ...options,
  modifiers: [
    ...(options.modifiers ?? []),
    {
      name: 'arrow',
      options: {
        padding: ARROW_PADDING,
      },
    },
  ],
});
