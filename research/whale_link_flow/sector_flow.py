import numpy as np
from typing import Dict, List
from .sector_map import get_sector

class SectorFlowEngine:
    @staticmethod
    def compute_sector_flow(live_flow_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Computes the average live flow score for each sector.
        """
        sector_scores = {}
        sector_counts = {}
        
        for asset, score in live_flow_scores.items():
            if np.isnan(score):
                continue
                
            sector = get_sector(asset)
            if sector not in sector_scores:
                sector_scores[sector] = 0.0
                sector_counts[sector] = 0
                
            sector_scores[sector] += score
            sector_counts[sector] += 1
            
        # Compute mean flow score for each sector
        final_scores = {}
        for sector in sector_scores.keys():
            count = sector_counts[sector]
            final_scores[sector] = sector_scores[sector] / count if count > 0 else 0.0
            
        # Ensure standard sectors are initialized even if no active assets (set to 0.0)
        all_sectors = ['L1', 'AI', 'MEME', 'DEX', 'INFRA', 'EXCHANGE']
        for s in all_sectors:
            if s not in final_scores:
                final_scores[s] = 0.0
                
        return final_scores
