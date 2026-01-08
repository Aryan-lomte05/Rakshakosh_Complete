"""
Context Builder - Enhanced for World-Class Answer Quality
Prioritizes matched chunks and adds clear section markers.
"""

class ContextBuilder:

    def build(self, chunks):
        """
        Build context with matched chunks first, clearly marked.
        """
        context_blocks = []
        citations = []
        
        # Separate matched vs neighbor chunks
        matched_chunks = [c for c in chunks if c.get("is_matched", False)]
        neighbor_chunks = [c for c in chunks if not c.get("is_matched", False)]
        
        # Add matched chunks first with clear marker
        if matched_chunks:
            context_blocks.append("=== MOST RELEVANT PASSAGES ===")
            for c in matched_chunks:
                block = f"[{c['doc_name']} | Page {c['page_start']}]\n{c['text']}"
                context_blocks.append(block)
                citations.append({
                    "source": c["doc_name"],
                    "page": c["page_start"],
                    "quote": c["text"][:200],
                    "is_primary": True
                })
        
        # Add neighbor chunks as supporting context
        if neighbor_chunks:
            context_blocks.append("\n=== SUPPORTING CONTEXT ===")
            for c in neighbor_chunks[:5]:  # Limit to 5 neighbors
                block = f"[{c['doc_name']} | Page {c['page_start']}]\n{c['text']}"
                context_blocks.append(block)
                citations.append({
                    "source": c["doc_name"],
                    "page": c["page_start"],
                    "quote": c["text"][:200],
                    "is_primary": False
                })

        return "\n\n".join(context_blocks), citations

