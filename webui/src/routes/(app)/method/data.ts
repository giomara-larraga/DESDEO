import type { Method } from './schemas';

export const methods: Method[] = [
  {
    name: "Interactive RVEA",
    shortName: "irvea",
    preferencesType: ["reference point", "preferred ranges", "preferred solutions"],
    problemtypes: ["linear", "nonlinear"]
  },
  {
    name: "Interactive K-RVEA",
    shortName: "ikrvea",
    preferencesType: ["reference point"],
    problemtypes: ["expensive"]
  },
  {
    name: "NIMBUS",
    shortName: "nimbus",
    variants: [
      {
        name: "Synchronous",
        preferencesType: ["classification"],
        problemtypes: ["nonlinear", "multiobjective"]
      },
      {
        name: "Asynchronous",
        preferencesType: ["classification"],
        problemtypes: ["nonlinear", "multiobjective"]
      }
    ]
  },
  {
    name: "Reference Point",
    preferencesType: ["reference point"],
    problemtypes: ["linear", "nonlinear"]
  }
];