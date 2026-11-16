import {
  LAUNCH_TARGET,
  allowIncompleteLaunch,
  publishedEssays,
} from '../scripts/essays.mjs';

export default function launchGate() {
  return {
    name: 'oropis-launch-gate',
    hooks: {
      'astro:build:start': () => {
        const ready = publishedEssays().length;
        if (ready >= LAUNCH_TARGET || allowIncompleteLaunch()) return;

        const remaining = LAUNCH_TARGET - ready;
        throw new Error(
          `Launch gate blocked the build: ${ready} of ${LAUNCH_TARGET} essays are ready. ` +
            `Publish ${remaining} more essay${remaining === 1 ? '' : 's'} with draft: false, ` +
            'or set ALLOW_INCOMPLETE_LAUNCH=true to build an incomplete preview. ' +
            'Run npm run launch-check for details.',
        );
      },
    },
  };
}
