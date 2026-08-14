"""Backward-compatible imports for older deployments and integrations."""

from services.supabase import SupabaseBackend, SupabaseError

__all__ = ["SupabaseBackend", "SupabaseError"]
