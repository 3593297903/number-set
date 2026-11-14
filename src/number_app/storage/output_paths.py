"""Read-only destination validation shared by backup and export, not ABC."""
import stat
from pathlib import Path


def _directory_path(value):
    """Resolve existing links and a possibly nonexistent suffix; fail closed."""
    try:
        path=Path(value).resolve(strict=False)
        for ancestor in (path,*path.parents):
            try:
                mode=ancestor.stat().st_mode
            except FileNotFoundError:
                continue
            if not stat.S_ISDIR(mode):
                raise ValueError('路径或其祖先不是目录：'+str(ancestor))
        return path
    except (OSError,RuntimeError,ValueError,TypeError) as error:
        raise ValueError('无法安全解析目录：'+str(value)+'；'+str(error)) from error


def _exists(path):
    try:
        path.stat()
        return True
    except FileNotFoundError:
        return False


def ensure_safe_output_paths(destination_root,planned_target,*,workspace_root,registered_batch_dirs):
    """Return canonical write paths, rejecting protected/marked descendants.

    Only metadata is read. No directory, database, file or Catalog is created.
    Callers must use the returned paths for all subsequent output operations.
    """
    try:
        root=_directory_path(destination_root)
        target=_directory_path(planned_target)
        workspace=_directory_path(workspace_root)
        protected=[_directory_path(workspace/'batches'),_directory_path(workspace/'staging')]
        protected.extend(_directory_path(path) for path in registered_batch_dirs)
        for candidate in (root,target):
            if any(candidate.is_relative_to(boundary) for boundary in protected):
                raise ValueError('目标目录位于受保护批次或batches/staging保留区域内部，请选择独立目录：'+str(candidate))
            for ancestor in (candidate,*candidate.parents):
                if _exists(ancestor/'request.json') and any(_exists(ancestor/name) for name in ('manifest.json','items.jsonl','quotas.json')):
                    raise ValueError('目标目录位于可识别批次内部，请选择独立目录：'+str(candidate))
        return root,target
    except (OSError,RuntimeError) as error:
        raise ValueError('无法确认目标目录是否安全，已停止写入：'+str(error)) from error
