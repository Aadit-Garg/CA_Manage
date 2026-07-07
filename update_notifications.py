import re

# Admin Routes
file_path = 'app/admin/routes.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    (r"create_notification\(req\.employee_id, f\"Your '\{req\.request_type\}' request for '\{doc\.title if doc else 'Document'\}' was Approved\.\", url_for\('employee\.requests_list'\)\)",
     r"create_notification(req.employee_id, f\"Your '{req.request_type}' request for '{doc.title if doc else 'Document'}' was Approved.\", link=url_for('employee.requests_list'), title='Request Approved', category='approvals', priority='high', entity_type='ApprovalRequest', entity_id=req.id)"),
     
    (r"create_notification\(req\.employee_id, f\"Your '\{req\.request_type\}' request was Rejected\. Reason: \{reason\}\", url_for\('employee\.requests_list'\)\)",
     r"create_notification(req.employee_id, f\"Your '{req.request_type}' request was Rejected. Reason: {reason}\", link=url_for('employee.requests_list'), title='Request Rejected', category='approvals', priority='high', entity_type='ApprovalRequest', entity_id=req.id)")
]

for pat, rep in replacements:
    content = re.sub(pat, rep, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

# Employee Routes
file_path = 'app/employee/routes.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    (r"notify_admins\(f\"New Document Upload Request for '\{doc\.title\}' by \{current_user\.full_name\}\", url_for\('admin\.approvals_list'\)\)",
     r"notify_admins(f\"New Document Upload Request for '{doc.title}' by {current_user.full_name}\", link=url_for('admin.approvals_list'), title='New Upload Request', category='approvals', priority='high', entity_type='Document', entity_id=doc.id)"),
     
    (r"notify_admins\(f\"Document Replacement Request for '\{doc\.title\}' by \{current_user\.full_name\}\", url_for\('admin\.approvals_list'\)\)",
     r"notify_admins(f\"Document Replacement Request for '{doc.title}' by {current_user.full_name}\", link=url_for('admin.approvals_list'), title='Replacement Request', category='approvals', priority='high', entity_type='Document', entity_id=doc.id)"),
     
    (r"notify_admins\(f\"Metadata Edit Request for '\{doc\.title\}' by \{current_user\.full_name\}\", url_for\('admin\.approvals_list'\)\)",
     r"notify_admins(f\"Metadata Edit Request for '{doc.title}' by {current_user.full_name}\", link=url_for('admin.approvals_list'), title='Edit Request', category='approvals', priority='normal', entity_type='Document', entity_id=doc.id)"),
     
    (r"notify_admins\(f\"Delete Document Request for '\{doc\.title\}' by \{current_user\.full_name\}\", url_for\('admin\.approvals_list'\)\)",
     r"notify_admins(f\"Delete Document Request for '{doc.title}' by {current_user.full_name}\", link=url_for('admin.approvals_list'), title='Delete Request', category='approvals', priority='high', entity_type='Document', entity_id=doc.id)"),
     
    (r"notify_admins\(f\"Password Edit Request for '\{doc\.title\}' by \{current_user\.full_name\}\", url_for\('admin\.approvals_list'\)\)",
     r"notify_admins(f\"Password Edit Request for '{doc.title}' by {current_user.full_name}\", link=url_for('admin.approvals_list'), title='Password Edit Request', category='approvals', priority='high', entity_type='Document', entity_id=doc.id)")
]

for pat, rep in replacements:
    content = re.sub(pat, rep, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated notification calls')
