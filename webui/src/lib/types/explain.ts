export interface RXIMOExplanation {
    shap_values: number[][];     // SHAP values for each objective
    base_values: number[];       // Base values for each objective
    explained_data: number[][];  // The data that was explained
}
