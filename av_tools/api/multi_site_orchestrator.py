import frappe
import requests
from frappe import _
from urllib.parse import urljoin

@frappe.whitelist()
def disable_user_on_all_sites(email, site_configuration_name):
    """
    Disable user across all enabled sites in a Site Configuration.
    """
    if not email:
        frappe.throw(_("Email is required"))
    
    if not site_configuration_name:
        frappe.throw(_("Site Configuration name is required"))
    
    site_config = frappe.get_doc("Site Configuration", site_configuration_name)
    
    if not site_config.sites:
        frappe.throw(_("No sites configured"))
    
    results = []
    
    for site_entry in site_config.sites:
        if not site_entry.enabled:
            results.append({
                "site_name": site_entry.site_name,
                "site_url": site_entry.site_url,
                "status": "skipped",
                "message": "Site disabled in configuration"
            })
            continue
        
        result = _disable_user_on_site(
            email=email,
            site_name=site_entry.site_name,
            site_url=site_entry.site_url,
            api_key=site_entry.api_key,
            api_secret=site_entry.get_password("api_secret")
        )
        results.append(result)
    
    return {
        "email": email,
        "configuration": site_configuration_name,
        "action": "disable",
        "total_sites": len(site_config.sites),
        "enabled_sites": len([s for s in site_config.sites if s.enabled]),
        "results": results
    }


@frappe.whitelist()
def enable_user_on_all_sites(email, site_configuration_name):
    """
    Enable user across all enabled sites in a Site Configuration.
    """
    if not email:
        frappe.throw(_("Email is required"))
    
    if not site_configuration_name:
        frappe.throw(_("Site Configuration name is required"))
    
    site_config = frappe.get_doc("Site Configuration", site_configuration_name)
    
    if not site_config.sites:
        frappe.throw(_("No sites configured"))
    
    results = []
    
    for site_entry in site_config.sites:
        if not site_entry.enabled:
            results.append({
                "site_name": site_entry.site_name,
                "site_url": site_entry.site_url,
                "status": "skipped",
                "message": "Site disabled in configuration"
            })
            continue
        
        result = _enable_user_on_site(
            email=email,
            site_name=site_entry.site_name,
            site_url=site_entry.site_url,
            api_key=site_entry.api_key,
            api_secret=site_entry.get_password("api_secret")
        )
        results.append(result)
    
    return {
        "email": email,
        "configuration": site_configuration_name,
        "action": "enable",
        "total_sites": len(site_config.sites),
        "enabled_sites": len([s for s in site_config.sites if s.enabled]),
        "results": results
    }


def _disable_user_on_site(email, site_name, site_url, api_key, api_secret):
    """Call remote site API to disable user."""
    try:
        if not site_url.startswith(("http://", "https://")):
            site_url = f"https://{site_url}"
        
        endpoint = urljoin(
            site_url,
            "/api/method/av_tools.api.user_management.disable_user_account"
        )
        
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"token {api_key}:{api_secret}",
                "Content-Type": "application/json"
            },
            json={"email": email},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            api_result = data.get("message", {})
            
            return {
                "site_name": site_name,
                "site_url": site_url,
                "status": "success" if api_result.get("success") else "failed",
                "message": api_result.get("message", "Unknown response")
            }
        else:
            return {
                "site_name": site_name,
                "site_url": site_url,
                "status": "error",
                "message": f"HTTP {response.status_code}: {response.text[:200]}"
            }
            
    except requests.exceptions.Timeout:
        return {
            "site_name": site_name,
            "site_url": site_url,
            "status": "error",
            "message": "Timeout after 30 seconds"
        }
    except requests.exceptions.ConnectionError:
        return {
            "site_name": site_name,
            "site_url": site_url,
            "status": "error",
            "message": "Connection failed - check URL"
        }
    except Exception as e:
        frappe.log_error(
            title=f"Multi-site user disable error: {site_name}",
            message=f"Site: {site_url}\nEmail: {email}\nError: {str(e)}"
        )
        return {
            "site_name": site_name,
            "site_url": site_url,
            "status": "error",
            "message": f"Exception: {str(e)}"
        }


def _enable_user_on_site(email, site_name, site_url, api_key, api_secret):
    """Call remote site API to enable user."""
    try:
        if not site_url.startswith(("http://", "https://")):
            site_url = f"https://{site_url}"
        
        endpoint = urljoin(
            site_url,
            "/api/method/av_tools.api.user_management.enable_user_account"
        )
        
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"token {api_key}:{api_secret}",
                "Content-Type": "application/json"
            },
            json={"email": email},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            api_result = data.get("message", {})
            
            return {
                "site_name": site_name,
                "site_url": site_url,
                "status": "success" if api_result.get("success") else "failed",
                "message": api_result.get("message", "Unknown response")
            }
        else:
            return {
                "site_name": site_name,
                "site_url": site_url,
                "status": "error",
                "message": f"HTTP {response.status_code}: {response.text[:200]}"
            }
            
    except requests.exceptions.Timeout:
        return {
            "site_name": site_name,
            "site_url": site_url,
            "status": "error",
            "message": "Timeout after 30 seconds"
        }
    except requests.exceptions.ConnectionError:
        return {
            "site_name": site_name,
            "site_url": site_url,
            "status": "error",
            "message": "Connection failed - check URL"
        }
        return {
            "site_name": site_name,
            "site_url": site_url,
            "status": "error",
            "message": f"Exception: {str(e)}"
        }

@frappe.whitelist()
def update_site_configuration(doc):
    """
    Update an existing Site Configuration document, including the child table.
    """
    doc = frappe._dict(doc)
    
    existing_doc = frappe.get_doc("Site Configuration", doc.name)
    existing_doc.title = doc.title
    existing_doc.description = doc.description
    
    # Clear existing sites and add new ones
    existing_doc.sites = []
    for site_entry in doc.sites:
        existing_doc.append("sites", site_entry)
        
    existing_doc.save(ignore_permissions=True)
    
    return existing_doc


