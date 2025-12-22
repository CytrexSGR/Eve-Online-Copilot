/**
 * Type Definitions
 */

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tool_calls?: ToolCall[];
  timestamp: Date;
}

export interface ToolCall {
  tool: string;
  input: any;
  result: any;
}

export interface ChatContext {
  characterId?: number;
  regionId: number;
  sessionId: string;
}

export interface Character {
  character_id: number;
  name: string;
  corporation?: string;
}

export interface Region {
  region_id: number;
  name: string;
}

// EVE Online data
export const MAJOR_REGIONS: Region[] = [
  { region_id: 10000002, name: 'The Forge (Jita)' },
  { region_id: 10000043, name: 'Domain (Amarr)' },
  { region_id: 10000030, name: 'Heimatar (Rens)' },
  { region_id: 10000032, name: 'Sinq Laison (Dodixie)' },
  { region_id: 10000042, name: 'Metropolis (Hek)' }
];
