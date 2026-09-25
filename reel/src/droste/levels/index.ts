/** Level registry. Module agents overwrite the four level files; this file stays as is. */
import type {LevelModule} from '../types';
import {L0} from './L0Prompt';
import {L1} from './L1Diff';
import {L2} from './L2Eye';
import {L3} from './L3Merges';

export const LEVELS: LevelModule[] = [L0, L1, L2, L3];
