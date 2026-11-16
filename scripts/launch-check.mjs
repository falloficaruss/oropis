import {
  LAUNCH_TARGET,
  allowIncompleteLaunch,
  publishedEssays,
  readEssays,
} from './essays.mjs';

const all = readEssays();
const ready = publishedEssays();
const drafts = all.length - ready.length;

console.log(`${ready.length} of ${LAUNCH_TARGET} essays ready`);

if (ready.length >= LAUNCH_TARGET) {
  console.log('Launch gate passed.');
} else {
  const remaining = LAUNCH_TARGET - ready.length;
  console.error(
    `Launch gate blocked: ${remaining} more non-draft essay${remaining === 1 ? '' : 's'} needed.`,
  );
  console.error(`${drafts} draft${drafts === 1 ? '' : 's'} hidden from production.`);

  if (allowIncompleteLaunch()) {
    console.error('ALLOW_INCOMPLETE_LAUNCH is active; incomplete builds are allowed.');
  } else {
    console.error('To build an incomplete preview, set ALLOW_INCOMPLETE_LAUNCH=true.');
  }

  process.exitCode = 1;
}
