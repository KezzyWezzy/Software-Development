"""
Example Usage of P&ID OCR Agent
Demonstrates how to use the agent for autonomous processing
"""
import requests
import time
from pathlib import Path

# API Base URL
API_BASE_URL = "http://localhost:8000/api/v1"


def upload_and_process_pid(file_path: str, project_name: str = "Example Project"):
    """
    Upload a P&ID document and start autonomous processing

    Args:
        file_path: Path to P&ID file
        project_name: Project name

    Returns:
        Task ID for monitoring
    """
    print(f"📤 Uploading {file_path}...")

    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'project_name': project_name,
            'pid_reference': Path(file_path).stem,
            'auto_process': 'true'
        }

        response = requests.post(
            f"{API_BASE_URL}/documents/upload",
            files=files,
            data=data
        )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Upload successful!")
        print(f"   Document ID: {result['document_id']}")
        print(f"   Task ID: {result['task_id']}")
        return result['task_id']
    else:
        print(f"❌ Upload failed: {response.text}")
        return None


def monitor_task(task_id: str, poll_interval: int = 5):
    """
    Monitor task progress until completion

    Args:
        task_id: Task identifier
        poll_interval: Seconds between status checks
    """
    print(f"\n👀 Monitoring task {task_id}...")
    print("   (This runs autonomously - no approval needed)")

    while True:
        response = requests.get(f"{API_BASE_URL}/tasks/{task_id}")

        if response.status_code == 200:
            result = response.json()
            status = result['status']

            if status == 'PENDING':
                print("   ⏳ Task pending...")
            elif status == 'PROCESSING':
                meta = result.get('meta', {})
                print(f"   🔄 Processing: {meta.get('status', 'Working...')}")
            elif status == 'SUCCESS':
                print("   ✅ Task completed successfully!")
                print_results(result['result'])
                break
            elif status == 'FAILURE':
                print(f"   ❌ Task failed: {result.get('error', 'Unknown error')}")
                break

            time.sleep(poll_interval)
        else:
            print(f"   ❌ Failed to get status: {response.text}")
            break


def print_results(result: dict):
    """Print processing results"""
    print("\n" + "=" * 60)
    print("📊 PROCESSING RESULTS")
    print("=" * 60)

    # OCR Results
    if 'ocr_result' in result:
        ocr = result['ocr_result']['result']
        print(f"\n📝 OCR Processing:")
        print(f"   Pages processed: {ocr.get('page_count', 0)}")
        print(f"   Instruments found: {ocr.get('instrument_count', 0)}")
        print(f"   Line numbers found: {ocr.get('line_count', 0)}")

    # Symbol Analysis
    if 'symbol_result' in result:
        symbols = result['symbol_result']
        print(f"\n🔍 Symbol Analysis:")
        print(f"   Symbols detected: {symbols.get('symbols_count', 0)}")
        print(f"   Lines detected: {symbols.get('lines_count', 0)}")
        print(f"   Connections found: {symbols.get('connections_count', 0)}")

    # HAZOP Results
    if 'hazop_result' in result:
        hazop = result['hazop_result']
        print(f"\n⚠️  HAZOP Study:")
        print(f"   Nodes analyzed: {hazop.get('nodes_count', 0)}")
        print(f"   Deviations identified: {hazop.get('deviations_count', 0)}")
        print(f"   High-risk items: {hazop.get('high_risk_count', 0)}")

    # Instrument Index
    if 'index_result' in result:
        index = result['index_result']
        print(f"\n📋 Instrument Index:")
        print(f"   Instruments cataloged: {index.get('instrument_count', 0)}")

        stats = index.get('statistics', {})
        if 'by_measured_variable' in stats:
            print(f"\n   By Measured Variable:")
            for var, count in stats['by_measured_variable'].items():
                print(f"      {var}: {count}")

    print("\n" + "=" * 60)


def batch_process_directory(directory: str, project_name: str):
    """
    Process all P&IDs in a directory autonomously

    Args:
        directory: Directory containing P&ID files
        project_name: Project name
    """
    print(f"\n📁 Batch processing directory: {directory}")

    pid_dir = Path(directory)
    pid_files = list(pid_dir.glob("*.pdf")) + list(pid_dir.glob("*.png"))

    if not pid_files:
        print("   No P&ID files found!")
        return

    print(f"   Found {len(pid_files)} files")

    # Upload all files
    files_data = []
    for file_path in pid_files:
        with open(file_path, 'rb') as f:
            files_data.append(('files', f))

    data = {'project_name': project_name}

    print("   📤 Uploading batch...")
    response = requests.post(
        f"{API_BASE_URL}/documents/batch-upload",
        files=files_data,
        data=data
    )

    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Batch upload successful!")
        print(f"      Task ID: {result['task_id']}")
        print(f"      Processing {result['document_count']} documents")
        print(f"\n   🤖 System is now processing autonomously...")
        print(f"      Monitor progress at: http://localhost:5555")

        # Monitor the batch task
        monitor_task(result['task_id'], poll_interval=10)
    else:
        print(f"   ❌ Batch upload failed: {response.text}")


def main():
    """Main example"""
    print("=" * 60)
    print("P&ID OCR Agent - Example Usage")
    print("Autonomous 24/7 Processing")
    print("=" * 60)

    # Example 1: Process single document
    print("\n" + "=" * 60)
    print("Example 1: Process Single P&ID")
    print("=" * 60)

    # task_id = upload_and_process_pid(
    #     "path/to/your/pid.pdf",
    #     "My Project"
    # )
    #
    # if task_id:
    #     monitor_task(task_id)

    # Example 2: Batch processing
    print("\n" + "=" * 60)
    print("Example 2: Batch Process Directory")
    print("=" * 60)

    # batch_process_directory(
    #     "path/to/pid/directory",
    #     "Batch Processing Project"
    # )

    # Example 3: Check system health
    print("\n" + "=" * 60)
    print("Example 3: System Health Check")
    print("=" * 60)

    response = requests.get(f"{API_BASE_URL.replace('/api/v1', '')}/health")
    if response.status_code == 200:
        health = response.json()
        print(f"✅ System Status: {health['status']}")
        print(f"   App: {health['app_name']}")
        print(f"   Version: {health['version']}")
    else:
        print("❌ System not responding")

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\nFor more examples, check the documentation:")
    print("  - docs/INTEGRATION_GUIDE.md")
    print("  - docs/DEPLOYMENT_GUIDE.md")
    print("\nAPI Documentation:")
    print("  http://localhost:8000/docs")
    print("\nWorker Monitoring:")
    print("  http://localhost:5555")
    print("=" * 60)


if __name__ == "__main__":
    main()
