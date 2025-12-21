"""
Enhanced Protocol Downloader Service.

Provides improved downloading of procurement protocols with better error handling,
reporting, and monitoring capabilities.
"""

import os
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from ..core.config import get_config
from ..vpn_utils import ensure_vpn_connected, check_zakupki_access, get_vpn_status, is_openvpn_running, is_vpn_interface_up, check_vpn_routes
from .utils import sanitize_filename, get_metadata_client, check_zakupki_health

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


@dataclass
class DownloadResult:
    """Enhanced result of download operation."""
    status: str
    message: str
    processed: int = 0
    downloaded: int = 0
    failed: int = 0
    duration: float = 0.0
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    statistics: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.statistics is None:
            self.statistics = {}


class EnhancedProtocolDownloader:
    """Enhanced service for downloading procurement protocols."""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the enhanced downloader.
        
        Args:
            output_dir: Directory for saving downloaded files
        """
        self.config = get_config().downloader
        self.output_dir = output_dir or self.config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize counters for statistics
        self.reset_counters()
        
        # Create session with retry mechanism
        self.session = self._create_session()
        
        logger.info(f"Initialized EnhancedProtocolDownloader with output dir: {self.output_dir}")

    def reset_counters(self):
        """Reset all internal counters."""
        self.counters = {
            "file_sizes": [],
            "download_times": [],
            "error_types": {},
            "file_types": {},
            "success_by_domain": {},
            "failed_by_domain": {}
        }

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry mechanism and proper headers.
        
        Returns:
            Configured requests session
        """
        session = requests.Session()
        
        # Set up retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "OPTIONS"]
        )
        
        # Mount adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update(self.config.browser_headers)
        
        return session

    def _update_statistics(self, url: str, file_size: int, download_time: float, success: bool):
        """
        Update internal statistics counters.
        
        Args:
            url: Downloaded URL
            file_size: Size of downloaded file in bytes
            download_time: Time taken to download in seconds
            success: Whether download was successful
        """
        # Track file sizes and download times
        self.counters["file_sizes"].append(file_size)
        self.counters["download_times"].append(download_time)
        
        # Track file types
        file_extension = Path(url).suffix.lower() if '.' in url else "unknown"
        self.counters["file_types"][file_extension] = \
            self.counters["file_types"].get(file_extension, 0) + 1
        
        # Track success/failure by domain
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if success:
                self.counters["success_by_domain"][domain] = \
                    self.counters["success_by_domain"].get(domain, 0) + 1
            else:
                self.counters["failed_by_domain"][domain] = \
                    self.counters["failed_by_domain"].get(domain, 0) + 1
        except Exception:
            pass  # Ignore parsing errors

    def _collect_statistics(self) -> Dict[str, Any]:
        """
        Collect detailed statistics from counters.
        
        Returns:
            Dictionary with statistics
        """
        stats = {}
        
        # File size statistics
        if self.counters["file_sizes"]:
            stats["file_sizes"] = {
                "total_bytes": sum(self.counters["file_sizes"]),
                "average_bytes": sum(self.counters["file_sizes"]) / len(self.counters["file_sizes"]),
                "max_bytes": max(self.counters["file_sizes"]),
                "min_bytes": min(self.counters["file_sizes"])
            }
        
        # Download time statistics
        if self.counters["download_times"]:
            stats["download_times"] = {
                "total_seconds": sum(self.counters["download_times"]),
                "average_seconds": sum(self.counters["download_times"]) / len(self.counters["download_times"]),
                "max_seconds": max(self.counters["download_times"]),
                "min_seconds": min(self.counters["download_times"])
            }
        
        # File type distribution
        stats["file_types"] = self.counters["file_types"]
        
        # Success/failure by domain
        stats["success_by_domain"] = self.counters["success_by_domain"]
        stats["failed_by_domain"] = self.counters["failed_by_domain"]
        
        # Error type distribution
        stats["error_types"] = self.counters["error_types"]
        
        return stats

    def _download_single_file(self, url: str, output_path: Path) -> bool:
        """
        Download a single file with enhanced error handling.
        
        Args:
            url: URL to download
            output_path: Path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()
        file_size = 0
        
        try:
            logger.debug(f"Downloading {url} to {output_path}")
            
            # Create parent directories
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Make request
            response = self.session.get(
                url,
                timeout=self.config.download_http_timeout,
                stream=True
            )
            response.raise_for_status()
            
            # Save file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Get file size
            file_size = output_path.stat().st_size
            
            # Calculate download time
            download_time = time.time() - start_time
            
            # Update statistics
            self._update_statistics(url, file_size, download_time, True)
            
            logger.info(f"Successfully downloaded {url} ({file_size} bytes in {download_time:.2f}s)")
            return True
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout downloading {url}"
            logger.error(error_msg)
            self.counters["error_types"]["timeout"] = \
                self.counters["error_types"].get("timeout", 0) + 1
            self._update_statistics(url, file_size, time.time() - start_time, False)
            return False
            
        except requests.exceptions.ConnectionError:
            error_msg = f"Connection error downloading {url}"
            logger.error(error_msg)
            self.counters["error_types"]["connection"] = \
                self.counters["error_types"].get("connection", 0) + 1
            self._update_statistics(url, file_size, time.time() - start_time, False)
            return False
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error {e.response.status_code} downloading {url}"
            logger.error(error_msg)
            error_type = f"http_{e.response.status_code}"
            self.counters["error_types"][error_type] = \
                self.counters["error_types"].get(error_type, 0) + 1
            self._update_statistics(url, file_size, time.time() - start_time, False)
            return False
            
        except Exception as e:
            error_msg = f"Error downloading {url}: {str(e)}"
            logger.error(error_msg)
            self.counters["error_types"]["other"] = \
                self.counters["error_types"].get("other", 0) + 1
            self._update_statistics(url, file_size, time.time() - start_time, False)
            return False

    def _process_single_protocol(self, protocol: Dict[str, Any], collection) -> Dict[str, Any]:
        """
        Process a single protocol with enhanced error handling.
        
        Args:
            protocol: Protocol document from MongoDB
            collection: MongoDB collection for updates
            
        Returns:
            Dictionary with processing results
        """
        unit_id = protocol.get("unit_id")
        urls = protocol.get("urls", [])
        
        if not unit_id:
            return {"downloaded": 0, "failed": 1, "error": "Protocol missing unit_id"}
        
        if not urls:
            try:
                collection.update_one(
                    {"unit_id": unit_id},
                    {"$set": {"status": "downloaded", "updated_at": datetime.utcnow()}}
                )
                return {"downloaded": 0, "failed": 0}
            except Exception as e:
                return {"downloaded": 0, "failed": 1, "error": f"Error updating status: {e}"}
        
        # Extract loadDate from protocol for directory structure
        load_date = protocol.get("loadDate")
        if isinstance(load_date, datetime):
            date_str = load_date.strftime("%Y-%m-%d")
        elif isinstance(load_date, str):
            # Try to parse string date
            try:
                date_obj = datetime.strptime(load_date, "%Y-%m-%d")
                date_str = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                # Fallback to current date if parsing fails
                date_str = datetime.utcnow().strftime("%Y-%m-%d")
        else:
            # Fallback to current date if loadDate is missing or invalid
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Create directory structure: Data/YYYY-MM-DD/Input/UNIT_xxx/
        date_dir = self.output_dir / date_str / "Input"
        unit_dir = date_dir / unit_id
        unit_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Created unit directory: {unit_dir} for protocol {unit_id} (date: {date_str})")
        
        downloaded_count = 0
        failed_count = 0
        
        # Limit number of URLs to download
        urls_to_download = urls[:self.config.max_urls_per_protocol]
        
        # Download files concurrently
        with ThreadPoolExecutor(max_workers=self.config.download_concurrency) as executor:
            futures = []
            
            for i, url_info in enumerate(urls_to_download):
                url = url_info.get("url")
                if not url:
                    continue
                
                # Create filename
                original_name = url_info.get("fileName") or f"document_{i+1}.pdf"
                safe_name = sanitize_filename(original_name)
                file_path = unit_dir / safe_name
                
                future = executor.submit(self._download_single_file, url, file_path)
                futures.append((future, file_path, url))
            
            # Collect results
            for future, file_path, url in futures:
                try:
                    success = future.result()
                    if success:
                        downloaded_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error waiting for download result for {url}: {e}")
        
        # Update protocol status in MongoDB
        try:
            collection.update_one(
                {"unit_id": unit_id},
                {"$set": {"status": "downloaded", "updated_at": datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"Error updating status for {unit_id}: {e}")
            failed_count += 1
        
        return {
            "downloaded": downloaded_count,
            "failed": failed_count,
            "error": None if failed_count == 0 else f"Failed to download {failed_count} documents"
        }

    def process_pending_protocols(self, limit: int = 0, target_date: Optional[datetime] = None) -> DownloadResult:
        """
        Process pending protocols with enhanced error handling and reporting.
        
        Args:
            limit: Maximum number of protocols to process (0 = no limit)
            target_date: Optional date to filter protocols by loadDate
            
        Returns:
            DownloadResult with detailed metrics
        """
        start_time = time.time()
        self.reset_counters()
        
        logger.info(f"Starting protocol processing with limit: {limit or 'no limit'}")
        
        # Check VPN connection before downloading
        logger.info("Checking VPN connection for zakupki.gov.ru access...")
        
        # Получаем детальный статус VPN
        vpn_status = get_vpn_status()
        
        # Логируем детальную информацию о VPN
        logger.info(f"VPN Status: OpenVPN running={vpn_status['openvpn_running']}, "
                   f"Interface up={vpn_status['interface_up']}, "
                   f"Overall status={vpn_status['overall_status']}")
        
        # Проверяем OpenVPN процесс
        if not vpn_status["openvpn_running"]:
            error_msg = "OpenVPN process is not running. Please start OpenVPN first."
            logger.error(error_msg)
            vpn_config = os.environ.get('VPN_CONFIG_FILE', '/root/winners_preprocessor/vitaly_bychkov.ovpn')
            logger.error(f"Example: sudo openvpn --config {vpn_config}")
            return DownloadResult(
                status="error",
                message=error_msg,
                duration=0.0,
                errors=[error_msg]
            )
        
        # Проверяем VPN интерфейс
        if not vpn_status["interface_up"]:
            error_msg = "VPN interface (tun0/tap0) is not up. VPN tunnel may not be established."
            logger.error(error_msg)
            return DownloadResult(
                status="error",
                message=error_msg,
                duration=0.0,
                errors=[error_msg]
            )
        
        # Проверяем маршруты к zakupki.gov.ru
        routes = check_vpn_routes(["zakupki.gov.ru", "www.zakupki.gov.ru"])
        if not any(routes.values()):
            logger.warning("Route to zakupki.gov.ru not found through VPN interface.")
            logger.warning("This may indicate that route-up-zakupki.sh was not executed or VPN routes are not configured.")
        
        # Проверяем доступность через ensure_vpn_connected для дополнительной проверки
        vpn_connected, vpn_message = ensure_vpn_connected()
        if not vpn_connected:
            logger.error(f"VPN check failed: {vpn_message}")
            return DownloadResult(
                status="error",
                message=f"VPN connection required: {vpn_message}",
                duration=0.0,
                errors=[f"VPN not connected: {vpn_message}"]
            )
        
        # Check zakupki.gov.ru availability
        logger.info("Checking zakupki.gov.ru availability...")
        zakupki_accessible, zakupki_url, response_time = check_zakupki_access()
        if not zakupki_accessible:
            return DownloadResult(
                status="error",
                message=f"zakupki.gov.ru unavailable: {zakupki_url}",
                duration=0.0,
                errors=[f"zakupki.gov.ru unavailable: {zakupki_url}"]
            )
        
        logger.info(f"zakupki.gov.ru is available (response time: {response_time:.2f}s)")
        
        # Connect to MongoDB
        logger.info("Connecting to MongoDB...")
        client = get_metadata_client()
        if not client:
            return DownloadResult(
                status="error",
                message="Failed to connect to MongoDB",
                duration=0.0,
                errors=["MongoDB connection failed"]
            )
        
        try:
            # Get database and collection
            db = client[self.config.mongo.db]
            collection = db[self.config.mongo.collection]
            logger.info("Connected to MongoDB")
            
            # Find pending protocols
            logger.info("Finding pending protocols...")
            query = {"status": "pending", "source": "remote_mongo_direct"}
            
            # Add date filter if specified
            if target_date:
                # Filter by loadDate (can be datetime or string)
                date_start = datetime.combine(target_date.date(), datetime.min.time())
                date_end = datetime.combine(target_date.date(), datetime.max.time())
                query["loadDate"] = {"$gte": date_start, "$lte": date_end}
                logger.info(f"Filtering by date: {target_date.strftime('%Y-%m-%d')}")
            
            cursor = collection.find(query)
            
            if limit > 0:
                cursor = cursor.limit(limit)
            
            protocols = list(cursor)
            logger.info(f"Found {len(protocols)} pending protocols")
            
            if not protocols:
                return DownloadResult(
                    status="success",
                    message="No pending protocols to process",
                    duration=0.0
                )
            
            # Process protocols concurrently
            logger.info(f"Processing {len(protocols)} protocols...")
            processed = 0
            downloaded = 0
            failed = 0
            errors = []
            warnings = []
            
            with ThreadPoolExecutor(max_workers=self.config.protocols_concurrency) as executor:
                futures = []
                
                for protocol in protocols:
                    if limit > 0 and processed >= limit:
                        break
                    
                    future = executor.submit(self._process_single_protocol, protocol, collection)
                    futures.append(future)
                    processed += 1
                
                # Collect results
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        downloaded += result.get("downloaded", 0)
                        failed += result.get("failed", 0)
                        if result.get("error"):
                            errors.append(result["error"])
                    except Exception as e:
                        failed += 1
                        error_msg = f"Error processing protocol: {str(e)}"
                        errors.append(error_msg)
                        self.counters["error_types"]["protocol_processing"] = \
                            self.counters["error_types"].get("protocol_processing", 0) + 1
                        logger.error(error_msg)
            
            # Collect final statistics
            duration = time.time() - start_time
            statistics = self._collect_statistics()
            
            result = DownloadResult(
                status="success" if failed == 0 else "partial",
                message="Protocol processing completed",
                processed=processed,
                downloaded=downloaded,
                failed=failed,
                duration=duration,
                errors=errors,
                warnings=warnings,
                statistics=statistics
            )
            
            # Log summary
            logger.info("Protocol processing completed:")
            logger.info(f"  Processed: {processed}")
            logger.info(f"  Downloaded: {downloaded}")
            logger.info(f"  Failed: {failed}")
            logger.info(f"  Duration: {duration:.2f} seconds")
            
            return result
            
        except Exception as e:
            error_msg = f"Critical error during protocol processing: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return DownloadResult(
                status="error",
                message=error_msg,
                duration=time.time() - start_time,
                errors=[error_msg]
            )
            
        finally:
            if client:
                client.close()
                logger.debug("Closed MongoDB connection")

    def get_download_summary(self) -> Dict[str, Any]:
        """
        Get a summary of download activities.
        
        Returns:
            Dictionary with download summary
        """
        return {
            "output_directory": str(self.output_dir),
            "total_files_downloaded": len(list(self.output_dir.rglob("*"))),
            "directories_created": len([d for d in self.output_dir.rglob("*") if d.is_dir()])
        }


def main():
    """Entry point for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Protocol Downloader")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of protocols to process (0 = no limit)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for downloaded files"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create downloader
    output_dir = Path(args.output_dir) if args.output_dir else None
    downloader = EnhancedProtocolDownloader(output_dir=output_dir)
    
    try:
        # Process protocols
        result = downloader.process_pending_protocols(limit=args.limit)
        
        # Print results
        print("\n" + "="*60)
        print("📥 DOWNLOAD RESULTS")
        print("="*60)
        
        if result.status == "success":
            print("✅ SUCCESS!")
        elif result.status == "partial":
            print("⚠️  PARTIAL SUCCESS (with errors)")
        else:
            print("❌ ERROR!")
        
        print(f"   Processed protocols: {result.processed}")
        print(f"   Downloaded documents: {result.downloaded}")
        print(f"   Failed downloads: {result.failed}")
        print(f"   Duration: {result.duration:.2f} seconds")
        
        if result.errors:
            print("\n📝 Errors:")
            for i, error in enumerate(result.errors[:5], 1):
                print(f"   {i}. {error[:100]}{'...' if len(error) > 100 else ''}")
            if len(result.errors) > 5:
                print(f"   ... and {len(result.errors) - 5} more errors")
        
        if result.warnings:
            print("\n⚠️  Warnings:")
            for i, warning in enumerate(result.warnings[:3], 1):
                print(f"   {i}. {warning}")
        
        if result.statistics:
            stats = result.statistics
            print("\n📈 Statistics:")
            
            if "file_sizes" in stats:
                fs = stats["file_sizes"]
                print(f"   File Sizes:")
                print(f"     Total: {fs['total_bytes']:,} bytes")
                print(f"     Average: {fs['average_bytes']:.0f} bytes")
                print(f"     Max: {fs['max_bytes']:,} bytes")
            
            if "download_times" in stats:
                dt = stats["download_times"]
                print(f"   Download Times:")
                print(f"     Total: {dt['total_seconds']:.2f} seconds")
                print(f"     Average: {dt['average_seconds']:.2f} seconds")
            
            if "file_types" in stats and stats["file_types"]:
                print(f"   File Types:")
                for ext, count in sorted(stats["file_types"].items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"     {ext}: {count}")
            
            if "error_types" in stats and stats["error_types"]:
                print(f"   Error Types:")
                for error_type, count in stats["error_types"].items():
                    print(f"     {error_type}: {count}")
        
        return 0 if result.status in ["success", "partial"] else 1
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())