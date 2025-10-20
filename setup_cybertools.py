"""
Setup script for the Cybersecurity Tools Management System.
This script will initialize the database with sample categories and tools.
"""
import asyncio
import sys
from sqlalchemy import select

# Add parent directory to path to import modules
sys.path.insert(0, '.')

from db import init_db, AsyncSessionLocal
from db.models import Category, Tool


async def setup_sample_data():
    """Initialize the database with sample categories and tools."""
    
    print("Initializing database...")
    await init_db()
    
    async with AsyncSessionLocal() as session:
        # Check if data already exists
        result = await session.execute(select(Category))
        existing_categories = result.scalars().all()
        
        if existing_categories:
            print(f"Database already contains {len(existing_categories)} categories.")
            response = input("Do you want to add sample data anyway? (y/n): ")
            if response.lower() != 'y':
                print("Setup cancelled.")
                return
        
        # Sample categories
        categories_data = [
            {
                "name": "Network Scanners",
                "description": "Tools for network discovery, port scanning, and network mapping"
            },
            {
                "name": "Web Vulnerability",
                "description": "Tools for web application security testing and vulnerability assessment"
            },
            {
                "name": "Exploitation",
                "description": "Exploitation frameworks and tools for penetration testing"
            },
            {
                "name": "Forensics",
                "description": "Digital forensics and incident response tools"
            },
            {
                "name": "OSINT",
                "description": "Open-source intelligence gathering and reconnaissance tools"
            },
            {
                "name": "Password Tools",
                "description": "Password cracking, recovery, and hash analysis tools"
            },
            {
                "name": "Wireless Security",
                "description": "WiFi and wireless network security assessment tools"
            },
            {
                "name": "Reverse Engineering",
                "description": "Tools for analyzing and reverse engineering software and binaries"
            }
        ]
        
        # Sample tools
        tools_data = [
            # Network Scanners
            {
                "name": "Nmap",
                "description": "Nmap (Network Mapper) is a free and open source utility for network discovery and security auditing. It uses raw IP packets to determine what hosts are available on the network, what services those hosts are offering, what operating systems they are running, and other characteristics.",
                "url": "https://nmap.org/",
                "category": "Network Scanners"
            },
            {
                "name": "Masscan",
                "description": "MASSCAN is an Internet-scale port scanner capable of scanning the entire Internet in under 6 minutes, transmitting 10 million packets per second. It produces results similar to nmap but is much faster.",
                "url": "https://github.com/robertdavidgraham/masscan",
                "category": "Network Scanners"
            },
            # Web Vulnerability
            {
                "name": "Burp Suite",
                "description": "Burp Suite is an integrated platform for performing security testing of web applications. It contains various tools for different testing methods including proxy, scanner, intruder, repeater, and more.",
                "url": "https://portswigger.net/burp",
                "category": "Web Vulnerability"
            },
            {
                "name": "OWASP ZAP",
                "description": "The OWASP Zed Attack Proxy (ZAP) is one of the world's most popular free security tools. It can help you automatically find security vulnerabilities in your web applications while you are developing and testing.",
                "url": "https://www.zaproxy.org/",
                "category": "Web Vulnerability"
            },
            {
                "name": "SQLMap",
                "description": "sqlmap is an open source penetration testing tool that automates the process of detecting and exploiting SQL injection flaws and taking over database servers.",
                "url": "https://sqlmap.org/",
                "category": "Web Vulnerability"
            },
            # Exploitation
            {
                "name": "Metasploit",
                "description": "The Metasploit Framework is a tool for developing and executing exploit code against a remote target machine. It is one of the most powerful and popular penetration testing frameworks.",
                "url": "https://www.metasploit.com/",
                "category": "Exploitation"
            },
            {
                "name": "ExploitDB",
                "description": "The Exploit Database is a CVE compliant archive of public exploits and corresponding vulnerable software, developed for use by penetration testers and vulnerability researchers.",
                "url": "https://www.exploit-db.com/",
                "category": "Exploitation"
            },
            # Forensics
            {
                "name": "Autopsy",
                "description": "Autopsy is a digital forensics platform and graphical interface to The Sleuth Kit and other digital forensics tools. It is used for analyzing disk images and recovering files.",
                "url": "https://www.autopsy.com/",
                "category": "Forensics"
            },
            {
                "name": "Volatility",
                "description": "Volatility is an advanced memory forensics framework. It is used for incident response and malware analysis by extracting digital artifacts from volatile memory (RAM) samples.",
                "url": "https://www.volatilityfoundation.org/",
                "category": "Forensics"
            },
            # OSINT
            {
                "name": "theHarvester",
                "description": "theHarvester is a simple to use, yet powerful and effective tool designed to be used in the early stages of a penetration test or red team engagement for gathering e-mails, names, subdomains, IPs and URLs.",
                "url": "https://github.com/laramies/theHarvester",
                "category": "OSINT"
            },
            {
                "name": "Maltego",
                "description": "Maltego is an open source intelligence and forensics application that provides a library of transforms for discovery of data from open sources and visualizing that information in a graph format.",
                "url": "https://www.maltego.com/",
                "category": "OSINT"
            },
            # Password Tools
            {
                "name": "John the Ripper",
                "description": "John the Ripper is a fast password cracker, currently available for many flavors of Unix, Windows, DOS, and OpenVMS. Its primary purpose is to detect weak Unix passwords.",
                "url": "https://www.openwall.com/john/",
                "category": "Password Tools"
            },
            {
                "name": "Hashcat",
                "description": "Hashcat is the world's fastest and most advanced password recovery utility, supporting five unique modes of attack for over 300 highly-optimized hashing algorithms.",
                "url": "https://hashcat.net/hashcat/",
                "category": "Password Tools"
            },
            # Wireless Security
            {
                "name": "Aircrack-ng",
                "description": "Aircrack-ng is a complete suite of tools to assess WiFi network security. It focuses on different areas of WiFi security: monitoring, attacking, testing, and cracking.",
                "url": "https://www.aircrack-ng.org/",
                "category": "Wireless Security"
            },
            {
                "name": "Kismet",
                "description": "Kismet is a wireless network and device detector, sniffer, wardriving tool, and WIDS (wireless intrusion detection) framework.",
                "url": "https://www.kismetwireless.net/",
                "category": "Wireless Security"
            },
            # Reverse Engineering
            {
                "name": "Ghidra",
                "description": "Ghidra is a software reverse engineering framework developed by NSA. It includes a suite of full-featured, high-end software analysis tools that enable users to analyze compiled code on a variety of platforms.",
                "url": "https://ghidra-sre.org/",
                "category": "Reverse Engineering"
            },
            {
                "name": "IDA Pro",
                "description": "IDA Pro is a powerful disassembler and debugger for analyzing malicious code and reverse engineering software. It supports a multitude of processors and file formats.",
                "url": "https://hex-rays.com/ida-pro/",
                "category": "Reverse Engineering"
            }
        ]
        
        print("\nCreating categories...")
        categories = {}
        for cat_data in categories_data:
            # Check if category exists
            result = await session.execute(
                select(Category).where(Category.name == cat_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"  - Category '{cat_data['name']}' already exists, skipping.")
                categories[cat_data["name"]] = existing
            else:
                category = Category(**cat_data)
                session.add(category)
                await session.flush()
                categories[cat_data["name"]] = category
                print(f"  + Created category: {cat_data['name']}")
        
        print("\nCreating tools...")
        for tool_data in tools_data:
            # Check if tool exists
            result = await session.execute(
                select(Tool).where(Tool.name == tool_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"  - Tool '{tool_data['name']}' already exists, skipping.")
            else:
                category_name = tool_data.pop("category")
                category = categories[category_name]
                
                tool = Tool(
                    **tool_data,
                    category_id=category.id
                )
                session.add(tool)
                print(f"  + Created tool: {tool_data['name']} ({category_name})")
        
        await session.commit()
        
        print("\n✅ Database setup complete!")
        print(f"   - Created {len(categories)} categories")
        print(f"   - Created {len(tools_data)} tools")
        print("\nYou can now use the /tools command in Discord to browse the tools.")


if __name__ == "__main__":
    print("=" * 60)
    print("Cybersecurity Tools Database Setup")
    print("=" * 60)
    
    try:
        asyncio.run(setup_sample_data())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()

