from flask import render_template, request, jsonify, url_for
from flask_login import current_user
from ..auth.decorators import admin_required
from ..models.user import User
from ..models.client import ClientProfile
from ..models.employee import Employee
from ..models.document import Document
from ..models.saved_filter import SavedFilter
from ..extensions import db
from . import admin_bp

@admin_bp.route('/search')
@admin_required
def global_search():
    """Global search across clients, employees, and documents."""
    q = request.args.get('q', '').strip()
    
    results = {
        'clients': [],
        'employees': [],
        'documents': []
    }
    
    if q:
        # Search Clients (by name, email, phone, company)
        results['clients'] = ClientProfile.query.filter(
            (ClientProfile.company_name.ilike(f'%{q}%')) |
            (ClientProfile.contact_person.ilike(f'%{q}%')) |
            (ClientProfile.email.ilike(f'%{q}%')) |
            (ClientProfile.phone.ilike(f'%{q}%'))
        ).limit(10).all()
        
        # Search Employees
        results['employees'] = Employee.query.filter(
            (Employee.full_name.ilike(f'%{q}%')) |
            (Employee.email.ilike(f'%{q}%')) |
            (Employee.phone.ilike(f'%{q}%')) |
            (Employee.designation.ilike(f'%{q}%'))
        ).limit(10).all()
        
        # Search Documents
        results['documents'] = Document.query.filter(
            (Document.title.ilike(f'%{q}%')) |
            (Document.category.ilike(f'%{q}%')) |
            (Document.financial_year.ilike(f'%{q}%'))
        ).limit(10).all()

    return render_template('admin/search/results.html', query=q, results=results)


@admin_bp.route('/saved-filters', methods=['GET', 'POST'])
@admin_required
def handle_saved_filters():
    """API for managing saved filters (AJAX)."""
    if request.method == 'POST':
        data = request.json
        name = data.get('name')
        module = data.get('module')
        filter_state = data.get('filter_state')
        
        if not all([name, module, filter_state]):
            return jsonify({'error': 'Missing data'}), 400
            
        sf = SavedFilter(
            user_id=current_user.id,
            name=name,
            module=module,
            filter_state=filter_state
        )
        db.session.add(sf)
        db.session.commit()
        return jsonify({'status': 'success', 'id': sf.id})
        
    # GET: return list of filters for a module
    module = request.args.get('module')
    if not module:
        return jsonify({'error': 'Module required'}), 400
        
    filters = SavedFilter.query.filter_by(user_id=current_user.id, module=module).order_by(SavedFilter.created_at.desc()).all()
    return jsonify({
        'filters': [{
            'id': f.id,
            'name': f.name,
            'filter_state': f.filter_state
        } for f in filters]
    })
    
@admin_bp.route('/saved-filters/<int:id>', methods=['DELETE'])
@admin_required
def delete_saved_filter(id):
    sf = SavedFilter.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(sf)
    db.session.commit()
    return jsonify({'status': 'success'})
