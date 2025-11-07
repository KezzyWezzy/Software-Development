"""
State Manager

Handles persistent state management for the entire agent team system.
Provides versioning, snapshots, and recovery capabilities.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib


class StateManager:
    """
    Manages system state with versioning and recovery capabilities.

    Features:
    - Versioned state snapshots (major.minor.patch)
    - Automatic and manual snapshots
    - State diffing between versions
    - Point-in-time recovery
    - State validation
    """

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.state_dir = workspace_dir / "state"
        self.backup_dir = workspace_dir / "backups" / "system"
        self.versions_file = self.state_dir / "versions.json"

        # Setup
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Version tracking
        self.current_version = self._load_current_version()
        self.versions: List[Dict[str, Any]] = self._load_version_history()

    def _load_current_version(self) -> str:
        """Load current version number"""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, 'r') as f:
                    data = json.load(f)
                    return data.get("current_version", "1.0.0")
            except:
                pass
        return "1.0.0"

    def _load_version_history(self) -> List[Dict[str, Any]]:
        """Load version history"""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, 'r') as f:
                    data = json.load(f)
                    return data.get("versions", [])
            except:
                pass
        return []

    def _save_version_history(self):
        """Save version history"""
        data = {
            "current_version": self.current_version,
            "versions": self.versions,
            "last_updated": datetime.utcnow().isoformat(),
        }
        with open(self.versions_file, 'w') as f:
            json.dump(data, f, indent=2)

    def create_snapshot(
        self,
        label: Optional[str] = None,
        increment: str = "patch",  # major, minor, or patch
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a state snapshot

        Args:
            label: Optional label for this snapshot
            increment: Version increment type (major, minor, patch)
            metadata: Optional metadata to store with snapshot

        Returns:
            New version number
        """
        # Increment version
        new_version = self._increment_version(self.current_version, increment)

        # Collect all state files
        state_files = self._collect_state_files()

        # Create snapshot directory
        snapshot_dir = self.backup_dir / f"v{new_version}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Copy state files
        for src_file in state_files:
            rel_path = src_file.relative_to(self.state_dir)
            dst_file = snapshot_dir / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

        # Calculate state hash
        state_hash = self._calculate_state_hash(state_files)

        # Create version entry
        version_entry = {
            "version": new_version,
            "label": label,
            "timestamp": datetime.utcnow().isoformat(),
            "increment_type": increment,
            "state_hash": state_hash,
            "file_count": len(state_files),
            "metadata": metadata or {},
            "snapshot_dir": str(snapshot_dir),
        }

        # Update history
        self.versions.append(version_entry)
        self.current_version = new_version
        self._save_version_history()

        return new_version

    def _increment_version(self, version: str, increment: str) -> str:
        """Increment version number"""
        major, minor, patch = map(int, version.split('.'))

        if increment == "major":
            major += 1
            minor = 0
            patch = 0
        elif increment == "minor":
            minor += 1
            patch = 0
        else:  # patch
            patch += 1

        return f"{major}.{minor}.{patch}"

    def _collect_state_files(self) -> List[Path]:
        """Collect all state files"""
        return list(self.state_dir.rglob("*.json"))

    def _calculate_state_hash(self, state_files: List[Path]) -> str:
        """Calculate hash of all state files"""
        hasher = hashlib.sha256()

        for file_path in sorted(state_files):
            with open(file_path, 'rb') as f:
                hasher.update(f.read())

        return hasher.hexdigest()

    def restore_snapshot(self, version: str) -> bool:
        """
        Restore system state to a specific version

        Args:
            version: Version number to restore

        Returns:
            True if successful
        """
        # Find version entry
        version_entry = None
        for v in self.versions:
            if v["version"] == version:
                version_entry = v
                break

        if not version_entry:
            return False

        snapshot_dir = Path(version_entry["snapshot_dir"])
        if not snapshot_dir.exists():
            return False

        # Create backup of current state before restoring
        self.create_snapshot(
            label=f"Before restore to v{version}",
            increment="patch"
        )

        # Clear current state
        for file_path in self._collect_state_files():
            file_path.unlink()

        # Restore files from snapshot
        for src_file in snapshot_dir.rglob("*.json"):
            rel_path = src_file.relative_to(snapshot_dir)
            dst_file = self.state_dir / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

        self.current_version = version
        self._save_version_history()

        return True

    def get_version_history(self) -> List[Dict[str, Any]]:
        """Get version history"""
        return self.versions.copy()

    def get_version_diff(self, version1: str, version2: str) -> Dict[str, Any]:
        """
        Get differences between two versions

        Args:
            version1: First version
            version2: Second version

        Returns:
            Diff information
        """
        v1_entry = next((v for v in self.versions if v["version"] == version1), None)
        v2_entry = next((v for v in self.versions if v["version"] == version2), None)

        if not v1_entry or not v2_entry:
            return {"error": "Version not found"}

        return {
            "version1": version1,
            "version2": version2,
            "time_diff": self._calculate_time_diff(v1_entry["timestamp"], v2_entry["timestamp"]),
            "hash_changed": v1_entry["state_hash"] != v2_entry["state_hash"],
            "file_count_diff": v2_entry["file_count"] - v1_entry["file_count"],
        }

    def _calculate_time_diff(self, time1: str, time2: str) -> str:
        """Calculate time difference between timestamps"""
        dt1 = datetime.fromisoformat(time1)
        dt2 = datetime.fromisoformat(time2)
        diff = abs((dt2 - dt1).total_seconds())

        if diff < 60:
            return f"{int(diff)} seconds"
        elif diff < 3600:
            return f"{int(diff / 60)} minutes"
        elif diff < 86400:
            return f"{int(diff / 3600)} hours"
        else:
            return f"{int(diff / 86400)} days"

    def validate_state(self) -> Dict[str, Any]:
        """
        Validate current system state

        Returns:
            Validation results
        """
        issues = []
        state_files = self._collect_state_files()

        # Check each state file
        for file_path in state_files:
            try:
                with open(file_path, 'r') as f:
                    json.load(f)  # Validate JSON
            except json.JSONDecodeError as e:
                issues.append({
                    "file": str(file_path),
                    "error": "Invalid JSON",
                    "details": str(e)
                })
            except Exception as e:
                issues.append({
                    "file": str(file_path),
                    "error": "Read error",
                    "details": str(e)
                })

        return {
            "valid": len(issues) == 0,
            "files_checked": len(state_files),
            "issues": issues,
            "current_version": self.current_version,
        }

    def cleanup_old_snapshots(self, keep_count: int = 50):
        """
        Clean up old snapshots, keeping only the most recent ones

        Args:
            keep_count: Number of snapshots to keep
        """
        if len(self.versions) <= keep_count:
            return

        # Sort by timestamp
        sorted_versions = sorted(self.versions, key=lambda v: v["timestamp"], reverse=True)

        # Keep recent versions
        keep_versions = sorted_versions[:keep_count]
        remove_versions = sorted_versions[keep_count:]

        # Remove old snapshots
        for version in remove_versions:
            snapshot_dir = Path(version["snapshot_dir"])
            if snapshot_dir.exists():
                shutil.rmtree(snapshot_dir)

        # Update version history
        self.versions = keep_versions
        self._save_version_history()
