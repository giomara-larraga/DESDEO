import Iterate from '@lucide/svelte/icons/repeat';
import Intermediate from '@lucide/svelte/icons/between-horizontal-start';
import History from '@lucide/svelte/icons/history';

export const CLASSIFICATION_TYPES = {
  ChangeFreely: 'Change freely',
  WorsenUntil: 'Impair until',
  KeepConstant: 'Keep constant at',
  ImproveUntil: 'Improve until',
  ImproveFreely: 'Improve freely'
};

export const PREFERENCE_TYPES = {
  ReferencePoint: 'Reference point',
  Classification: 'Classification',
  PreferredRange: 'Preferred range',
  PreferredSolution: 'Preferred solution',
  NonPreferredSolution: 'Non-preferred solution',
};

export const SIGNIFICANT_DIGITS = 2;

export const IMPROVING_COLOR = '#0C7BDC';
export const IMPAIRING_COLOR = '#DC3220';

export const options_segmented_control = [
	{ onlyIcon: true, icon: Iterate, value: 'iterate', label: 'Iterate' },
	{ onlyIcon: true, icon: Intermediate, value: 'intermediate', label: 'Find intermediate' },
	{ onlyIcon: true, icon: History, value: 'history', label: 'History' } 
];
