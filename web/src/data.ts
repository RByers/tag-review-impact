// The shape of data/public/reviews.json (tagimpact/build.py).

export interface Feature {
  id: number | null;
  name: string;
  link_source: 'tag_review' | 'other_field' | 'issue_body';
  i2s_url: string | null;
  i2p_url: string | null;
  ship_milestone: number | null;
  chrome_status: string;
  tag_review_status: string;
  has_origin_trial: boolean;
}

export interface TimelineComment {
  t: number;
  side: 'tag' | 'requester';
  login: string;
  id: number;
}

/** Labels for one review. Dimension keys map to a value key (single) or a list (multi). */
export interface Impact {
  [dimension: string]: unknown;
  reason: string;
  evidence_ids: number[];
  model: string;
  prompt_version: string;
}

export interface Review {
  number: number;
  title: string;
  kind: 'review' | 'charter' | 'question';
  requester: string;
  opened: string;
  closed: string | null;
  open: boolean;
  resolution: string | null;
  state_reason: string | null;
  total_days: number;
  author_wait_days: number;
  tag_days: number;
  label_wait_days: number;
  turn_wait_days: number;
  first_tag_comment_days: number | null;
  comments: number;
  tag_comments: number;
  requester_comments: number;
  wait_segments: [number, number][];
  timeline: TimelineComment[];
  review_type: string[];
  venues: string[];
  topics: string[];
  features: Feature[];
  impact: Impact | null;
}

export interface TaxonomyValue {
  key: string;
  label: string;
  definition: string;
  /** A CSS colour token from build (taxonomy.py), e.g. var(--seq-3). */
  color: string;
}

export interface Dimension {
  key: string;
  label: string;
  description: string;
  multi: boolean;
  ordinal: boolean;
  derived: boolean;
  /** Set when values come from a review field rather than the model labels. */
  field?: 'resolution';
  values: TaxonomyValue[];
}

export interface Dataset {
  generated: string;
  taxonomy: {
    version: string;
    dimensions: Dimension[];
    prompt?: { system: string; user: string };
    /** How the inferred stance agrees with the Resolution labels (build.stance_check). */
    stance_check?: { n: number; agreement: number; kappa: number | null };
    /** Resolution label -> stance group, for comparing the two. */
    resolution_stance?: Record<string, string>;
  };
  tag_logins: string[];
  reviews: Review[];
}

export async function load(): Promise<Dataset> {
  const r = await fetch('./reviews.json');
  if (!r.ok) throw new Error(`reviews.json: HTTP ${r.status}`);
  return JSON.parse(await r.text()) as Dataset;
}

/** Values a review has on a dimension (empty when unlabelled). */
export function valuesOf(r: Review, dim: Dimension): string[] {
  // Dimensions from GitHub structure (the Resolution label), not from a model.
  if (dim.field === 'resolution') return [r.resolution ?? 'none'];
  const v = r.impact?.[dim.key];
  if (typeof v === 'string') return [v];
  if (Array.isArray(v)) return v.filter((x): x is string => typeof x === 'string');
  return [];
}

export const year = (r: Review) => Number(r.opened.slice(0, 4));
