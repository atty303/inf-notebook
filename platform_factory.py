import platform
from platform_service import PlatformService

def create_platform_service() -> PlatformService:
    """Create appropriate platform service for current OS"""
    
    if platform.system() == 'Windows':
        from windows_platform import WindowsPlatformService
        return WindowsPlatformService()
    elif platform.system() == 'Linux':
        from linux_platform import LinuxPlatformService  
        return LinuxPlatformService()
    else:
        raise RuntimeError(f'Unsupported platform: {platform.system()}')

# Global platform service instance
_platform_service = None

def get_platform_service() -> PlatformService:
    """Get singleton platform service instance"""
    global _platform_service
    if _platform_service is None:
        _platform_service = create_platform_service()
    return _platform_service