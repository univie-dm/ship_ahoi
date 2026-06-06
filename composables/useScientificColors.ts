/**
 * Scientific color palettes and utilities for data visualization
 * Based on research-backed colorblind-friendly palettes
 */

// Viridis colormap (perceptually uniform, colorblind-friendly)
const VIRIDIS_COLORS = [
  '#440154', '#482878', '#3e4989', '#31688e', '#26828e',
  '#1f9e89', '#35b779', '#6ece58', '#b5de2b', '#fde725'
];

// Plasma colormap (high contrast, colorblind-friendly)  
const PLASMA_COLORS = [
  '#0d0887', '#46039f', '#7201a8', '#9c179e', '#bd3786',
  '#d8576b', '#ed7953', '#fb9f3a', '#fdca26', '#f0f921'
];

// Cividis colormap (colorblind-safe, blue-yellow)
const CIVIDIS_COLORS = [
  '#00224e', '#123570', '#3b496c', '#575d6d', '#707173',
  '#8a8678', '#a59c74', '#c3b369', '#e1cc55', '#fde725'
];

// Paul Tol's discrete colors (qualitative, research-backed)
const TOL_BRIGHT = [
  '#4477AA', '#EE6677', '#228833', '#CCBB44', '#66CCEE',
  '#AA3377', '#BBBBBB', '#000000'
];

const TOL_MUTED = [
  '#CC6677', '#332288', '#DDCC77', '#117733', '#88CCEE',
  '#882255', '#44AA99', '#999933', '#AA4499', '#DDDDDD'
];

const TOL_LIGHT = [
  '#77AADD', '#EE8866', '#EEDD88', '#FFAABB', '#99DDFF',
  '#44BB99', '#BBCC33', '#AAAA00', '#DDDDDD'
];

// IBM Carbon Design colors (accessible, professional)
const CARBON_CATEGORICAL = [
  '#6929c4', '#1192e8', '#005d5d', '#9f1853', '#fa4d56',
  '#570408', '#198038', '#002d9c', '#ee538b', '#b28600',
  '#009d9a', '#012749', '#8a3800', '#a56eff'
];

// Colorblind-safe qualitative palette (Paul Tol's muted + bright schemes).
// These hues stay distinguishable under deuteranopia, protanopia and tritanopia.
const COLORBLIND_SAFE = [
  // Tol muted (primary qualitative scheme, CVD-friendly)
  '#332288', '#88CCEE', '#44AA99', '#117733', '#999933',
  '#DDCC77', '#CC6677', '#882255', '#AA4499',
  // Tol bright (extra distinct hues for larger cluster counts)
  '#4477AA', '#EE6677', '#228833', '#CCBB44', '#66CCEE', '#AA3377'
];

// Scientific palette combinations for different use cases
export const SCIENTIFIC_PALETTES = {
  // Best for general purpose clustering (high contrast, colorblind-friendly)
  default: [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#4477AA', '#EE6677', '#228833', '#CCBB44', '#66CCEE',
    '#AA3377', '#CC6677', '#332288', '#DDCC77', '#117733'
  ],
  
  // Viridis-based discrete palette (perceptually uniform)
  viridis: VIRIDIS_COLORS,
  
  // Plasma-based discrete palette (high contrast)
  plasma: PLASMA_COLORS,
  
  // Cividis-based discrete palette (blue-yellow, colorblind-safe)
  cividis: CIVIDIS_COLORS,
  
  // Paul Tol research-backed colors
  tol_bright: TOL_BRIGHT,
  tol_muted: TOL_MUTED,
  tol_light: TOL_LIGHT,
  
  // IBM Carbon Design (professional, accessible)
  carbon: CARBON_CATEGORICAL,

  // Colorblind-safe qualitative palette (Paul Tol schemes)
  colorblind_safe: COLORBLIND_SAFE,
  
  // High contrast for small datasets (≤8 clusters)
  high_contrast: [
    '#e60049', '#0bb4ff', '#50e991', '#e6d800', '#9b19f5',
    '#ffa300', '#dc0ab4', '#b3d4ff', '#00bfa0'
  ],
  
  // Extended palette for large datasets (>10 clusters)
  extended: [
    // Primary distinctive colors
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    
    // Secondary colors from Tol palette
    '#4477AA', '#EE6677', '#228833', '#CCBB44', '#66CCEE',
    '#AA3377', '#CC6677', '#332288', '#DDCC77', '#117733',
    
    // Tertiary colors from Carbon
    '#6929c4', '#1192e8', '#005d5d', '#9f1853', '#fa4d56',
    '#570408', '#198038', '#002d9c', '#ee538b', '#b28600',
    
    // Additional colors for very large datasets
    '#009d9a', '#012749', '#8a3800', '#a56eff', '#be95ff',
    '#82cfff', '#42be65', '#ffb000', '#ff8389', '#ba4e00'
  ]
};

/**
 * Convert hex color to RGB values
 */
export function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

/**
 * Calculate luminance of a color (for contrast calculations)
 */
export function getLuminance(hex: string): number {
  const rgb = hexToRgb(hex);
  if (!rgb) return 0;
  
  const { r, g, b } = rgb;
  const [rs, gs, bs] = [r, g, b].map(c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Calculate contrast ratio between two colors
 */
export function getContrastRatio(color1: string, color2: string): number {
  const lum1 = getLuminance(color1);
  const lum2 = getLuminance(color2);
  const brightest = Math.max(lum1, lum2);
  const darkest = Math.min(lum1, lum2);
  return (brightest + 0.05) / (darkest + 0.05);
}

/**
 * Determine best highlighting color for a given background color
 * Returns either white or black based on contrast ratio
 */
export function getBestHighlightColor(backgroundColor: string): string {
  const whiteContrast = getContrastRatio(backgroundColor, '#ffffff');
  const blackContrast = getContrastRatio(backgroundColor, '#000000');
  
  // Use WCAG AA standard (4.5:1 ratio minimum)
  // Choose the color with higher contrast
  return whiteContrast > blackContrast ? '#ffffff' : '#000000';
}

/**
 * Get enhanced highlighting style for a color with excellent contrast
 */
export function getHighlightStyle(backgroundColor: string): {
  strokeColor: string;
  strokeWidth: number;
  glowColor: string;
  shadowColor: string;
} {
  // Always use black for the stroke color as requested
  const strokeColor = '#000000';
  const strokeWidth = 3;
  const glowColor = 'rgba(0, 0, 0, 0.7)';
  
  return {
    strokeColor,
    strokeWidth,
    glowColor,
    shadowColor: glowColor
  };
}

/**
 * Convert hex color to HSL
 */
function hexToHSL(hex: string): { h: number; s: number; l: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return null;
  
  let r = parseInt(result[1], 16) / 255;
  let g = parseInt(result[2], 16) / 255;
  let b = parseInt(result[3], 16) / 255;
  
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;
  
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }
  
  return { h: h * 360, s: s * 100, l: l * 100 };
}

/**
 * Get the appropriate scientific palette based on cluster count
 */
export function getScientificPalette(clusterCount: number, preferredPalette?: keyof typeof SCIENTIFIC_PALETTES): string[] {
  // Use preferred palette if specified and valid
  if (preferredPalette && SCIENTIFIC_PALETTES[preferredPalette]) {
    const palette = SCIENTIFIC_PALETTES[preferredPalette];
    if (palette.length >= clusterCount) {
      return palette.slice(0, clusterCount);
    }
    // If preferred palette is too small, fall through to automatic selection
  }
  
  // Automatic palette selection based on cluster count
  if (clusterCount <= 8) {
    return SCIENTIFIC_PALETTES.high_contrast.slice(0, clusterCount);
  } else if (clusterCount <= 10) {
    return SCIENTIFIC_PALETTES.tol_muted.slice(0, clusterCount);
  } else if (clusterCount <= 20) {
    return SCIENTIFIC_PALETTES.default.slice(0, clusterCount);
  } else {
    // For very large datasets, use extended palette with repetition if needed
    const extended = SCIENTIFIC_PALETTES.extended;
    if (clusterCount <= extended.length) {
      return extended.slice(0, clusterCount);
    } else {
      // Repeat palette with slight modifications for very large datasets
      const result = [...extended];
      let index = 0;
      while (result.length < clusterCount) {
        result.push(extended[index % extended.length]);
        index++;
      }
      return result.slice(0, clusterCount);
    }
  }
}

/**
 * Get a colorblind-safe categorical palette with `count` colors.
 * Uses Paul Tol's CVD-friendly qualitative schemes, cycling if more colors
 * are needed than the base palette provides.
 */
export function getColorblindPalette(count: number): string[] {
  const base = COLORBLIND_SAFE;
  if (count <= base.length) {
    return base.slice(0, count);
  }
  const result = [...base];
  let index = 0;
  while (result.length < count) {
    result.push(base[index % base.length]);
    index++;
  }
  return result;
}

/**
 * Validate color accessibility (WCAG standards)
 */
export function validateColorAccessibility(palette: string[]): {
  isAccessible: boolean;
  issues: string[];
  suggestions: string[];
} {
  const issues: string[] = [];
  const suggestions: string[] = [];
  
  // Check minimum contrast between adjacent colors
  for (let i = 0; i < palette.length - 1; i++) {
    const contrast = getContrastRatio(palette[i], palette[i + 1]);
    if (contrast < 2.0) {
      issues.push(`Low contrast between color ${i} and ${i + 1}: ${contrast.toFixed(2)}:1`);
    }
  }
  
  // Check if any colors are too similar
  const similarColors: string[] = [];
  for (let i = 0; i < palette.length; i++) {
    for (let j = i + 1; j < palette.length; j++) {
      const contrast = getContrastRatio(palette[i], palette[j]);
      if (contrast < 1.5) {
        similarColors.push(`Colors ${i} and ${j} are too similar`);
      }
    }
  }
  
  if (similarColors.length > 0) {
    issues.push(...similarColors);
    suggestions.push('Consider using a higher contrast palette like "high_contrast" or "tol_bright"');
  }
  
  if (palette.length > 10) {
    suggestions.push('For datasets with >10 clusters, consider grouping similar clusters or using hierarchical visualization');
  }
  
  return {
    isAccessible: issues.length === 0,
    issues,
    suggestions
  };
}

export default {
  SCIENTIFIC_PALETTES,
  getScientificPalette,
  getColorblindPalette,
  getBestHighlightColor,
  getHighlightStyle,
  validateColorAccessibility,
  hexToRgb,
  getLuminance,
  getContrastRatio
};
