import frappe
from frappe import _

@frappe.whitelist()
def disable_user_account(email):
    """
    Disable user account by email.
    Must be called with valid API credentials.
    """
    if not email:
        frappe.throw(_("Email is required"))
    
    email = email.strip().lower()
    
    if email == "administrator":
        return {
            "success": False,
            "message": "Cannot disable Administrator"
        }
    
    if not frappe.db.exists("User", email):
        return {
            "success": True,
            "message": f"User {email} does not exist"
        }
    
    user = frappe.get_doc("User", email)
    
    if user.enabled == 0:
        return {
            "success": True,
            "message": f"User {email} already disabled"
        }
    
    user.enabled = 0
    user.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {
        "success": True,
        "message": f"User {email} disabled"
    }


@frappe.whitelist()
def enable_user_account(email):
    """
    Enable user account by email.
    Must be called with valid API credentials.
    """
    if not email:
        frappe.throw(_("Email is required"))
    
    email = email.strip().lower()
    
    if not frappe.db.exists("User", email):
        return {
            "success": True,
            "message": f"User {email} does not exist"
        }
    
    user = frappe.get_doc("User", email)
    
    if user.enabled == 1:
        return {
            "success": True,
            "message": f"User {email} already enabled"
        }
    
    user.enabled = 1
    user.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {
        "success": True,
        "message": f"User {email} enabled"
    }
