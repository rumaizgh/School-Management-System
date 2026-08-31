/**
 * Web Admin Dashboard JavaScript Engine
 * Aligned 100% with Mobile Admin Module Specification
 */

const API_BASE = '/api';

// State Management
const state = {
  token: localStorage.getItem('access_token'),
  user: JSON.parse(localStorage.getItem('user_data') || 'null'),
  role: localStorage.getItem('user_role'),
  activeTab: 'dashboard',
  cache: {
    students: [],
    teachers: []
  }
};

// API Wrapper
async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('access_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  if (response.status === 401) {
    showToast('Session expired. Please log in again.', 'error');
    logout();
    throw new Error('Unauthorized');
  }

  let text = await response.text();
  let data = {};
  try {
    data = JSON.parse(text);
  } catch (e) {
    data = {};
  }

  if (!response.ok) {
    let errorMsg = `HTTP ${response.status} ${response.statusText}`;
    if (data.detail) {
      errorMsg = data.detail;
    } else if (data.error) {
      errorMsg = data.error;
    } else if (data.non_field_errors) {
      errorMsg = Array.isArray(data.non_field_errors) ? data.non_field_errors.join(', ') : data.non_field_errors;
    } else if (typeof data === 'object' && Object.keys(data).length > 0) {
      errorMsg = Object.entries(data)
        .map(([field, errs]) => `${field}: ${Array.isArray(errs) ? errs.join(', ') : errs}`)
        .join(' | ');
    }
    throw new Error(errorMsg);
  }

  return data;
}

// Toast Notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
    <div>${message}</div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Auth Helpers
function checkAuth() {
  if (!state.token || !state.user) {
    if (!window.location.pathname.includes('/login/')) {
      window.location.href = '/dashboard/login/';
    }
    return false;
  }
  return true;
}

function logout() {
  localStorage.clear();
  window.location.href = '/dashboard/login/';
}

// Modal Helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    populateModalDropdowns(modalId);
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
}

async function populateModalDropdowns(modalId) {
  try {
    // Populate Classes dropdowns
    if (['modalCreateStudent', 'modalEditStudent', 'modalCreateFee', 'modalCreateTimetable', 'modalEditTimetable', 'modalCreateExam', 'modalEditExam'].includes(modalId)) {
      const classSelects = document.querySelectorAll('#studentBatchSelect, #editStudentBatchSelect, #feeBatchSelect, #timetableClassSelect, #editTimetableClassSelect, #examBatchSelect, #editExamBatchSelect');
      if (classSelects.length) {
        const classes = await apiFetch('/academics/class/');
        const options = '<option value="">-- Select Class Batch --</option>' +
          (classes || []).map(c => `<option value="${c.id}">${c.classs}${c.section ? ' (' + c.section + ')' : ''} — ${c.year}</option>`).join('');
        classSelects.forEach(s => { s.innerHTML = options; });
      }
    }

    // Populate Students dropdowns
    if (modalId === 'modalCreateFee') {
      const studentSelect = document.getElementById('feeStudentSelect');
      if (studentSelect) {
        const students = await apiFetch('/account/students/');
        const list = Array.isArray(students) ? students : (students.results || []);
        studentSelect.innerHTML = '<option value="">-- Select Student --</option>' +
          list.map(s => `<option value="${s.id}">${s.name || s.email}${s.roll_number ? ' [Roll #' + s.roll_number + ']' : ''}</option>`).join('');
      }
    }

    // Populate Subjects dropdowns
    if (['modalCreateTimetable', 'modalEditTimetable', 'modalCreateExam', 'modalEditExam'].includes(modalId)) {
      const subjectSelects = document.querySelectorAll('#timetableSubjectSelect, #editTimetableSubjectSelect, #examSubjectSelect, #editExamSubjectSelect');
      if (subjectSelects.length) {
        const subjects = await apiFetch('/subject/');
        const options = '<option value="">-- Select Subject --</option>' +
          (subjects || []).map(sub => `<option value="${sub.id}">${sub.subject_name} (${sub.subject_code})</option>`).join('');
        subjectSelects.forEach(s => { s.innerHTML = options; });
      }
    }

    // Populate Teachers dropdowns
    if (['modalCreateTimetable', 'modalEditTimetable', 'modalCreatePayroll'].includes(modalId)) {
      const teacherSelects = document.querySelectorAll('#timetableTeacherSelect, #editTimetableTeacherSelect, #payrollTeacherSelect');
      if (teacherSelects.length) {
        const teachers = await apiFetch('/account/teachers/');
        const list = Array.isArray(teachers) ? teachers : (teachers.results || []);
        teacherSelects.forEach(s => {
          const isOptional = s.id.includes('Timetable');
          s.innerHTML = `<option value="">${isOptional ? '-- Select Teacher (Optional) --' : '-- Select Teacher --'}</option>` +
            list.map(t => `<option value="${t.id}">${t.name || t.email}</option>`).join('');
        });
      }
    }
  } catch (err) {
    console.error('Failed to populate dropdowns for', modalId, err);
  }
}

// DOM Loaded Initialization
document.addEventListener('DOMContentLoaded', () => {
  if (window.location.pathname.includes('/login/')) {
    initLoginPage();
  } else {
    if (!checkAuth()) return;
    initDashboardPage();
  }
});

// Login Logic
function initLoginPage() {
  const loginForm = document.getElementById('loginForm');
  if (!loginForm) return;

  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const btn = document.getElementById('btnLogin');

    btn.disabled = true;
    btn.innerText = 'Signing in...';

    try {
      const data = await apiFetch('/account/login/', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });

      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      localStorage.setItem('user_data', JSON.stringify(data.user));
      localStorage.setItem('user_role', data.role);

      showToast('Login successful! Redirecting...', 'success');
      setTimeout(() => {
        window.location.href = '/dashboard/';
      }, 500);
    } catch (err) {
      showToast(err.message, 'error');
      btn.disabled = false;
      btn.innerText = 'Sign In to Portal';
    }
  });
}

// Dashboard Page Main Logic
function initDashboardPage() {
  renderInstituteBranding();
  setupNavigation();
  loadTabContent('dashboard');
}

function renderInstituteBranding() {
  const user = state.user;
  if (!user) return;

  const adminNameEl = document.getElementById('adminName');
  if (adminNameEl) adminNameEl.innerText = user.name || user.email;

  const schoolNameEl = document.getElementById('schoolName');
  const schoolLogoEl = document.getElementById('schoolLogoContainer');

  const instDetails = user.institute_details;
  if (instDetails) {
    if (schoolNameEl) schoolNameEl.innerText = instDetails.name || 'School Portal';
    if (schoolLogoEl && instDetails.logo) {
      schoolLogoEl.innerHTML = `<img src="${instDetails.logo}" alt="Logo" />`;
    } else if (schoolLogoEl) {
      const firstLetter = (instDetails.name || 'S').charAt(0).toUpperCase();
      schoolLogoEl.innerHTML = `<span class="school-logo-placeholder">${firstLetter}</span>`;
    }
  } else {
    if (schoolNameEl) schoolNameEl.innerText = 'Superadmin Portal';
  }
}

function setupNavigation() {
  const navButtons = document.querySelectorAll('.nav-item button');
  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      if (!tab) return;

      navButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
      const activeSec = document.getElementById(`section-${tab}`);
      if (activeSec) activeSec.classList.add('active');

      const pageTitle = document.getElementById('pageTitle');
      if (pageTitle) pageTitle.innerText = btn.innerText.trim();

      state.activeTab = tab;
      loadTabContent(tab);
    });
  });
}

// Tab Content Loaders
function loadTabContent(tab) {
  switch (tab) {
    case 'dashboard':
      loadDashboardMetrics();
      break;
    case 'students':
      loadStudents();
      break;
    case 'teachers':
      loadTeachers();
      break;
    case 'classes':
      loadClasses();
      break;
    case 'subjects':
      loadSubjects();
      break;
    case 'timetable':
      loadTimetables();
      break;
    case 'exams':
      loadExams();
      break;
    case 'fees':
      loadFees();
      break;
    case 'payroll':
      loadPayroll();
      break;
    case 'attendance':
      loadAttendance();
      break;
  }
}

// 1. Dashboard Metrics
async function loadDashboardMetrics() {
  try {
    const res = await apiFetch('/account/getcount/');
    if (res.data) {
      document.getElementById('countStudents').innerText = res.data.students || 0;
      document.getElementById('countTeachers').innerText = res.data.teachers || 0;
      document.getElementById('countClasses').innerText = res.data.classes || 0;
      document.getElementById('countSubjects').innerText = res.data.subjects || 0;
    }
  } catch (err) {
    console.error('Failed to load counts:', err);
  }
}

// 2. Students Tab with Filters & Sorting
async function loadStudents() {
  const tbody = document.getElementById('studentsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;">Loading students...</td></tr>';

  try {
    const students = await apiFetch('/account/students/');
    state.cache.students = students;
    filterStudentsList();

    const searchInput = document.getElementById('searchStudentInput');
    if (searchInput) {
      searchInput.oninput = () => filterStudentsList();
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:var(--color-danger);">${err.message}</td></tr>`;
  }
}

function filterStudentsList() {
  let list = [...state.cache.students];
  const search = document.getElementById('searchStudentInput')?.value.toLowerCase().trim() || '';
  const gender = document.getElementById('filterStudentGender')?.value || '';
  const sort = document.getElementById('sortStudentBy')?.value || 'name_asc';

  if (search) {
    list = list.filter(s => 
      (s.name && s.name.toLowerCase().includes(search)) ||
      (s.email && s.email.toLowerCase().includes(search)) ||
      (s.phone && s.phone.includes(search))
    );
  }

  if (gender) {
    list = list.filter(s => (s.gender || '').toLowerCase() === gender.toLowerCase());
  }

  if (sort === 'name_asc') {
    list.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  } else if (sort === 'name_desc') {
    list.sort((a, b) => (b.name || '').localeCompare(a.name || ''));
  } else if (sort === 'newest') {
    list.sort((a, b) => b.id - a.id);
  } else if (sort === 'oldest') {
    list.sort((a, b) => a.id - b.id);
  }

  renderStudentsTable(list);
}

function renderStudentsTable(students) {
  const tbody = document.getElementById('studentsTableBody');
  if (!students.length) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;">No students found.</td></tr>';
    return;
  }

  tbody.innerHTML = students.map(s => {
    const batches = (s.classs && s.classs.length) ? s.classs.map(c => c.classs).join(', ') : 'Unassigned';
    return `
      <tr>
        <td><strong>#${s.roll_number || s.id}</strong></td>
        <td><strong>${s.name || 'N/A'}</strong></td>
        <td>${s.email || 'N/A'}</td>
        <td>${s.phone || 'N/A'}</td>
        <td>${s.parent_contact || 'N/A'}</td>
        <td><span class="badge-tag" style="text-transform:capitalize;">${s.gender || 'N/A'}</span></td>
        <td><span class="badge-tag">${batches}</span></td>
        <td>
          <span class="status-pill ${s.is_active ? 'status-active' : 'status-inactive'}">
            ${s.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="openEditStudentModal(${s.id})">Edit</button>
          ${s.is_active ? `<button class="btn btn-sm btn-danger" onclick="deactivateStudent(${s.id})">Deactivate</button>` : ''}
        </td>
      </tr>
    `;
  }).join('');
}

async function deactivateStudent(id) {
  if (!confirm('Are you sure you want to deactivate this student?')) return;
  try {
    await apiFetch(`/account/deletestudent/${id}/`, { method: 'DELETE' });
    showToast('Student deactivated successfully', 'success');
    loadStudents();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deactivateTeacher(id) {
  if (!confirm('Are you sure you want to deactivate this teacher?')) return;
  try {
    await apiFetch(`/account/deleteteacher/${id}/`, { method: 'DELETE' });
    showToast('Teacher deactivated successfully', 'success');
    loadTeachers();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 3. Teachers Tab with Gender Filters
async function loadTeachers() {
  const tbody = document.getElementById('teachersTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Loading teachers...</td></tr>';

  try {
    const teachers = await apiFetch('/account/teachers/');
    state.cache.teachers = teachers;
    filterTeachersList();

    const searchInput = document.getElementById('searchTeacherInput');
    if (searchInput) searchInput.oninput = () => filterTeachersList();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--color-danger);">${err.message}</td></tr>`;
  }
}

function filterTeachersList() {
  let list = [...state.cache.teachers];
  const search = document.getElementById('searchTeacherInput')?.value.toLowerCase().trim() || '';
  const gender = document.getElementById('filterTeacherGender')?.value || '';

  if (search) {
    list = list.filter(t => (t.name && t.name.toLowerCase().includes(search)) || (t.email && t.email.toLowerCase().includes(search)));
  }

  if (gender) {
    list = list.filter(t => (t.gender || '').toLowerCase() === gender.toLowerCase());
  }

  renderTeachersTable(list);
}

function renderTeachersTable(teachers) {
  const tbody = document.getElementById('teachersTableBody');
  if (!teachers.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No teachers found.</td></tr>';
    return;
  }

  tbody.innerHTML = teachers.map(t => {
    const subjects = (t.subjects && t.subjects.length) ? t.subjects.map(s => s.subject_name).join(', ') : 'None';
    return `
      <tr>
        <td><strong>${t.name || 'N/A'}</strong></td>
        <td>${t.email || 'N/A'}</td>
        <td>${t.phone || 'N/A'}</td>
        <td><span class="badge-tag" style="text-transform:capitalize;">${t.gender || 'N/A'}</span></td>
        <td>${subjects}</td>
        <td>
          <span class="status-pill ${t.is_active ? 'status-active' : 'status-inactive'}">
            ${t.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="openEditTeacherModal(${t.id})">Edit</button>
          ${t.is_active ? `<button class="btn btn-sm btn-danger" onclick="deactivateTeacher(${t.id})">Deactivate</button>` : ''}
        </td>
      </tr>
    `;
  }).join('');
}

// 4. Classes / Batches Tab
async function loadClasses() {
  const tbody = document.getElementById('classesTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Loading classes...</td></tr>';

  try {
    const batches = await apiFetch('/academics/class/');
    if (!batches.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No classes found.</td></tr>';
      return;
    }

    tbody.innerHTML = batches.map(b => `
      <tr>
        <td><strong>${b.classs}</strong></td>
        <td>${b.section || 'N/A'}</td>
        <td>${b.year || 'N/A'}</td>
        <td>Batch #${b.id}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="openEditClassModal(${b.id}, '${b.classs}', '${b.section || ''}', '${b.year}')">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="deleteClass(${b.id})">Delete</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--color-danger);">${err.message}</td></tr>`;
  }
}

function openEditClassModal(id, classs, section, year) {
  document.getElementById('editClassId').value = id;
  document.getElementById('editClassName').value = classs;
  document.getElementById('editClassSection').value = section;
  document.getElementById('editClassYear').value = year;
  openModal('modalEditClass');
}

async function handleEditClass(event) {
  event.preventDefault();
  const form = event.target;
  const id = form.id.value;
  const data = {
    classs: form.classs.value,
    section: form.section.value || null,
    year: form.year.value
  };

  try {
    await apiFetch(`/academics/class/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
    showToast('Class updated successfully!', 'success');
    closeModal('modalEditClass');
    loadClasses();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteClass(id) {
  if (!confirm('Are you sure you want to delete this class?')) return;
  try {
    await apiFetch(`/academics/class/${id}/`, { method: 'DELETE' });
    showToast('Class deleted', 'success');
    loadClasses();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 5. Subjects Tab
async function loadSubjects() {
  const tbody = document.getElementById('subjectsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Loading subjects...</td></tr>';

  try {
    const subjects = await apiFetch('/subject/');
    if (!subjects.length) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No subjects found.</td></tr>';
      return;
    }

    tbody.innerHTML = subjects.map(s => `
      <tr>
        <td><strong>${s.subject_name}</strong></td>
        <td><span class="badge-tag">${s.subject_code}</span></td>
        <td>${s.teacher_name || s.teacher || 'Unassigned'}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="openEditSubjectModal(${s.id}, '${(s.subject_name||'').replace(/'/g, "\\'")}', '${(s.subject_code||'').replace(/'/g, "\\'")}')">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="deleteSubject(${s.id})">Delete</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--color-danger);">${err.message}</td></tr>`;
  }
}

async function deleteSubject(id) {
  if (!confirm('Delete subject?')) return;
  try {
    await apiFetch(`/subject/deletesubject/${id}/`, { method: 'DELETE' });
    showToast('Subject deleted', 'success');
    loadSubjects();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 6. Timetables Tab
async function loadTimetables() {
  const tbody = document.getElementById('timetableTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Loading timetables...</td></tr>';

  try {
    const timetables = await apiFetch('/academics/timetables/');
    if (!timetables.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No schedules logged.</td></tr>';
      return;
    }

    tbody.innerHTML = timetables.map(t => `
      <tr>
        <td><strong style="text-transform:uppercase;">${t.day}</strong></td>
        <td>${t.start_time} - ${t.end_time}</td>
        <td>${t.classs_name || t.classs}</td>
        <td>${t.subject_name || t.subject}</td>
        <td>${t.teacher_name || t.teacher || 'N/A'}</td>
        <td>
          <span class="status-pill ${t.is_exam ? 'status-pending' : 'status-active'}">
            ${t.is_exam ? 'Exam Schedule' : 'Regular Class'}
          </span>
        </td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="openEditTimetableModal(${t.id}, ${t.classs || 'null'}, ${t.subject || 'null'}, ${t.teacher || 'null'}, '${t.day || ''}', '${t.start_time || ''}', '${t.end_time || ''}', ${t.is_exam})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="deleteTimetable(${t.id})">Delete</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--color-danger);">${err.message}</td></tr>`;
  }
}

async function deleteTimetable(id) {
  if (!confirm('Delete timetable schedule?')) return;
  try {
    await apiFetch(`/academics/timetables/${id}/`, { method: 'DELETE' });
    showToast('Timetable schedule deleted', 'success');
    loadTimetables();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 7. Exams & Marks Tab
async function loadExams() {
  const tbody = document.getElementById('examsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Loading exams...</td></tr>';

  try {
    const exams = await apiFetch('/academics/exams/');
    if (!exams.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No exams recorded.</td></tr>';
      return;
    }

    tbody.innerHTML = exams.map(e => `
      <tr>
        <td><strong>${e.exam_name}</strong></td>
        <td>${e.subject_name || e.subject || 'N/A'}</td>
        <td>${e.batch_name || e.batch || 'N/A'}</td>
        <td>${e.total_mark}</td>
        <td>${e.pass_mark}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="viewExamAnalytics(${e.id})">Analytics</button>
          <button class="btn btn-sm btn-primary" onclick="openBulkMarksModal(${e.id})">Enter Marks</button>
        </td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="openEditExamModal(${e.id}, '${(e.exam_name||'').replace(/'/g, "\\'")}', ${e.batch || 'null'}, ${e.subject || 'null'}, ${e.total_mark}, ${e.pass_mark})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="deleteExam(${e.id})">Delete</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--color-danger);">${err.message}</td></tr>`;
  }
}

async function viewExamAnalytics(examId) {
  try {
    const data = await apiFetch(`/academics/exams/${examId}/analytics/`);
    alert(`
📊 Exam Analytics:
• Total Students Attended: ${data.total_students_attended}
• Pass Percentage: ${data.pass_percentage}%
• Highest Mark: ${data.highest_mark ?? 'N/A'} (Top Scorer: ${data.top_scorer_name ?? 'N/A'})
• Average Mark: ${data.average_mark ?? 'N/A'}
• Lowest Mark: ${data.lowest_mark ?? 'N/A'}
    `);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function openBulkMarksModal(examId) {
  try {
    let inputStr = prompt("Enter Student ID and Obtained Mark (Format: student_id:mark, student_id:mark)\nExample: 12:85, 14:90");
    if (!inputStr) return;

    const parsedMarks = inputStr.split(',').map(pair => {
      const [sid, m] = pair.split(':');
      return { student_id: parseInt(sid.trim()), obtained_mark: parseFloat(m.trim()) };
    });

    await apiFetch(`/academics/exams/${examId}/marks/`, {
      method: 'POST',
      body: JSON.stringify({ marks: parsedMarks })
    });

    showToast('Marks updated successfully!', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteExam(id) {
  if (!confirm('Delete exam?')) return;
  try {
    await apiFetch(`/academics/exams/${id}/`, { method: 'DELETE' });
    showToast('Exam deleted', 'success');
    loadExams();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 8. Fees & Payments Tab
async function loadFees() {
  const tbody = document.getElementById('feesTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Loading fees...</td></tr>';

  try {
    const fees = await apiFetch('/academics/fee/');
    if (!fees.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No fee records found.</td></tr>';
      return;
    }

    tbody.innerHTML = fees.map(f => {
      const isPaid = (f.balance_amount !== undefined ? f.balance_amount <= 0 : f.paid);
      return `
        <tr>
          <td><strong>${f.student_name || f.student}</strong></td>
          <td>${f.description || 'Tuition Fee'}</td>
          <td>${f.batch_name || f.batch}</td>
          <td>₹${f.amount}</td>
          <td>${f.due_date || 'N/A'}</td>
          <td>
            <span class="status-pill ${isPaid ? 'status-paid' : 'status-unpaid'}">
              ${isPaid ? 'Paid' : 'Pending'}
            </span>
          </td>
          <td>
            <button class="btn btn-sm btn-secondary" onclick="openEditFeeModal(${f.id}, '${(f.description || '').replace(/'/g, "\\'")}', ${f.amount}, '${f.due_date || ''}')">Edit</button>
            <button class="btn btn-sm btn-primary" onclick="openPaymentModal(${f.id}, ${f.amount})">Record Payment</button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--color-danger);">${err.message}</td></tr>`;
  }
}

async function openPaymentModal(feeId, feeAmount) {
  // Open the payment recording modal instead of using prompt()
  document.getElementById('paymentFeeId').value = feeId;
  document.getElementById('paymentFeeLabel').innerText = `Fee #${feeId} — Total: ₹${feeAmount}`;
  document.getElementById('paymentAmountInput').value = '';
  document.getElementById('paymentMethodSelect').value = 'cash';
  openModal('modalRecordPayment');
}

async function handleRecordPayment(event) {
  event.preventDefault();
  const feeId = parseInt(document.getElementById('paymentFeeId').value);
  const amount = parseFloat(document.getElementById('paymentAmountInput').value);
  const method = document.getElementById('paymentMethodSelect').value;

  if (!amount || amount <= 0) {
    showToast('Please enter a valid payment amount.', 'error');
    return;
  }

  try {
    await apiFetch('/academics/payments/', {
      method: 'POST',
      body: JSON.stringify({
        fee: feeId,
        amount: amount,
        payment_method: method
      })
    });
    showToast('Payment recorded successfully!', 'success');
    closeModal('modalRecordPayment');
    loadFees();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 9. Payroll Tab
async function loadPayroll() {
  const tbody = document.getElementById('payrollTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">Loading payroll records...</td></tr>';

  try {
    const payrolls = await apiFetch('/academics/payrolls/');
    if (!payrolls.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No payroll disbursements recorded.</td></tr>';
      return;
    }

    tbody.innerHTML = payrolls.map(p => `
      <tr>
        <td><strong>${p.teacher_name || p.teacher}</strong></td>
        <td>${p.disbursement_month}</td>
        <td><span class="badge-tag" style="text-transform:uppercase;">${p.payment_method}</span></td>
        <td>${p.transaction_id || 'N/A'}</td>
        <td><strong>₹${p.amount}</strong></td>
        <td>${p.created_at || 'N/A'}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--color-danger);">${err.message}</td></tr>`;
  }
}

// 10. Attendance Tab
async function loadAttendance() {
  const tbody = document.getElementById('attendanceTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Loading attendance sessions...</td></tr>';

  try {
    // Correct endpoint: ViewAttendanceSessions — returns paginated response
    const data = await apiFetch('/attendance/viewsession/');
    // Handle both paginated ({results:[...]}) and plain array responses
    const sessions = data.results || data;

    if (!sessions || !sessions.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No attendance sessions found.</td></tr>';
      return;
    }

    tbody.innerHTML = sessions.map(s => `
      <tr>
        <td><strong>Session #${s.id}</strong></td>
        <td>${s.classs_name || s.classs || 'N/A'}</td>
        <td>${s.teacher_name || s.teacher || 'N/A'}</td>
        <td>${s.date || 'N/A'}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="viewAttendanceDetails(${s.id})">View Records</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--color-danger);">${err.message}</td></tr>`;
  }
}

async function viewAttendanceDetails(sessionId) {
  try {
    // Correct endpoint: AttendanceRecordView — GET /attendance/showatdrec/<id>/
    const records = await apiFetch(`/attendance/showatdrec/${sessionId}/`);
    const list = Array.isArray(records) ? records : (records.results || []);
    let details = list.map(r => `Student ID ${r.student}: ${(r.status || '').toUpperCase()}`).join('\n');
    alert(`📋 Session #${sessionId} Attendance:\n\n` + (details || 'No records logged.'));
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Form Handlers
async function handleCreateStudent(event) {
  event.preventDefault();
  const form = event.target;

  if (form.password.value !== form.confirm_password.value) {
    showToast('Passwords do not match!', 'error');
    return;
  }

  const data = {
    name: form.name.value,
    email: form.email.value || null,
    phone: form.phone.value,
    parent_contact: form.parent_contact.value || null,
    roll_number: form.roll_number.value || null,
    gender: form.gender.value,
    date_of_birth: form.date_of_birth.value || null,
    address: form.address.value || null,
    password: form.password.value,
    classs: form.batch_id.value ? [parseInt(form.batch_id.value)] : []
  };

  try {
    await apiFetch('/account/createstudent/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
    showToast('Student created successfully!', 'success');
    closeModal('modalCreateStudent');
    form.reset();
    loadStudents();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleCreateTeacher(event) {
  event.preventDefault();
  const form = event.target;
  const data = {
    name: form.name.value,
    email: form.email.value,
    phone: form.phone.value,
    gender: form.gender.value,
    password: form.password.value
  };

  try {
    await apiFetch('/account/createteacher/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
    showToast('Teacher created successfully!', 'success');
    closeModal('modalCreateTeacher');
    form.reset();
    loadTeachers();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleCreateClass(event) {
  event.preventDefault();
  const form = event.target;
  const data = {
    classs: form.classs.value,
    section: form.section.value || null,
    year: form.year.value
  };

  try {
    await apiFetch('/academics/class/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
    showToast('Class created successfully!', 'success');
    closeModal('modalCreateClass');
    form.reset();
    loadClasses();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleCreateSubject(event) {
  event.preventDefault();
  const form = event.target;
  const data = {
    subject_name: form.subject_name.value,
    subject_code: form.subject_code.value
  };

  try {
    await apiFetch('/subject/addsubject/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
    showToast('Subject added successfully!', 'success');
    closeModal('modalCreateSubject');
    form.reset();
    loadSubjects();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleCreateFee(event) {
  event.preventDefault();
  const form = event.target;
  const data = {
    student: parseInt(form.student_id.value),
    batch: parseInt(form.batch_id.value),
    amount: parseFloat(form.amount.value),
    description: form.description.value || 'Tuition Fee',
    due_date: form.due_date.value
  };

  try {
    await apiFetch('/academics/fee/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
    showToast('Fee structure created successfully!', 'success');
    closeModal('modalCreateFee');
    form.reset();
    loadFees();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleCreateTimetable(event) {
  event.preventDefault();
  const form = event.target;
  const data = {
    classs: parseInt(form.classs_id.value),
    subject: parseInt(form.subject_id.value),
    teacher: form.teacher_id.value ? parseInt(form.teacher_id.value) : null,
    day: form.day.value,
    start_time: form.start_time.value,
    end_time: form.end_time.value,
    is_exam: form.is_exam.value === 'true'
  };

  try {
    await apiFetch('/academics/timetables/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
    showToast('Timetable schedule saved successfully!', 'success');
    closeModal('modalCreateTimetable');
    form.reset();
    loadTimetables();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleCreatePayroll(event) {
  event.preventDefault();
  const form = event.target;
  const data = {
    teacher: parseInt(form.teacher_id.value),
    disbursement_month: form.disbursement_month.value,
    payment_method: form.payment_method.value,
    transaction_id: form.transaction_id.value || null,
    amount: parseFloat(form.amount.value),
    remarks: form.remarks.value || null
  };

  try {
    await apiFetch('/academics/payrolls/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
    showToast('Payroll disbursement recorded!', 'success');
    closeModal('modalCreatePayroll');
    form.reset();
    loadPayroll();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==========================================
// EDIT MODAL HANDLERS FOR ALL ENTITIES
// ==========================================

// 1. Student Edit Handlers
function openEditStudentModal(id) {
  const student = state.cache.students.find(s => s.id === id);
  if (!student) return;
  document.getElementById('editStudentId').value = student.id;
  document.getElementById('editStudentName').value = student.name || '';
  document.getElementById('editStudentEmail').value = student.email || '';
  document.getElementById('editStudentPhone').value = student.phone || '';
  document.getElementById('editStudentParentContact').value = student.parent_contact || '';
  document.getElementById('editStudentRollNumber').value = student.roll_number || '';
  document.getElementById('editStudentGender').value = student.gender || 'male';
  openModal('modalEditStudent');
  if (student.classs && student.classs.length) {
    setTimeout(() => {
      const batchSel = document.getElementById('editStudentBatchSelect');
      if (batchSel) batchSel.value = student.classs[0].id;
    }, 300);
  }
}

async function handleEditStudent(event) {
  event.preventDefault();
  const form = event.target;
  const id = form.id.value;
  const data = {
    name: form.name.value,
    email: form.email.value || null,
    phone: form.phone.value,
    parent_contact: form.parent_contact.value || null,
    roll_number: form.roll_number.value || null,
    gender: form.gender.value,
    classs: form.batch_id.value ? [parseInt(form.batch_id.value)] : []
  };

  try {
    await apiFetch(`/account/editstudent/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
    showToast('Student record updated successfully!', 'success');
    closeModal('modalEditStudent');
    loadStudents();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 2. Teacher Edit Handlers
function openEditTeacherModal(id) {
  const teacher = state.cache.teachers.find(t => t.id === id);
  if (!teacher) return;
  document.getElementById('editTeacherId').value = teacher.id;
  document.getElementById('editTeacherName').value = teacher.name || '';
  document.getElementById('editTeacherEmail').value = teacher.email || '';
  document.getElementById('editTeacherPhone').value = teacher.phone || '';
  document.getElementById('editTeacherGender').value = teacher.gender || 'female';
  openModal('modalEditTeacher');
}

async function handleEditTeacher(event) {
  event.preventDefault();
  const form = event.target;
  const id = form.id.value;
  const data = {
    name: form.name.value,
    email: form.email.value,
    phone: form.phone.value,
    gender: form.gender.value
  };

  try {
    await apiFetch(`/account/editteacher/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
    showToast('Teacher record updated successfully!', 'success');
    closeModal('modalEditTeacher');
    loadTeachers();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 3. Subject Edit Handlers
function openEditSubjectModal(id, name, code) {
  document.getElementById('editSubjectId').value = id;
  document.getElementById('editSubjectName').value = name;
  document.getElementById('editSubjectCode').value = code;
  openModal('modalEditSubject');
}

async function handleEditSubject(event) {
  event.preventDefault();
  const form = event.target;
  const id = form.id.value;
  const data = {
    subject_name: form.subject_name.value,
    subject_code: form.subject_code.value
  };

  try {
    await apiFetch(`/subject/editsubject/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
    showToast('Subject updated successfully!', 'success');
    closeModal('modalEditSubject');
    loadSubjects();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 4. Timetable Edit Handlers
function openEditTimetableModal(id, classId, subjectId, teacherId, day, startTime, endTime, isExam) {
  document.getElementById('editTimetableId').value = id;
  document.getElementById('editTimetableDay').value = day;
  document.getElementById('editTimetableStartTime').value = startTime;
  document.getElementById('editTimetableEndTime').value = endTime;
  document.getElementById('editTimetableIsExam').value = isExam ? 'true' : 'false';
  openModal('modalEditTimetable');
  setTimeout(() => {
    if (classId) document.getElementById('editTimetableClassSelect').value = classId;
    if (subjectId) document.getElementById('editTimetableSubjectSelect').value = subjectId;
    if (teacherId) document.getElementById('editTimetableTeacherSelect').value = teacherId;
  }, 300);
}

async function handleEditTimetable(event) {
  event.preventDefault();
  const form = event.target;
  const id = form.id.value;
  const data = {
    classs: parseInt(form.classs_id.value),
    subject: parseInt(form.subject_id.value),
    teacher: form.teacher_id.value ? parseInt(form.teacher_id.value) : null,
    day: form.day.value,
    start_time: form.start_time.value,
    end_time: form.end_time.value,
    is_exam: form.is_exam.value === 'true'
  };

  try {
    await apiFetch(`/academics/timetables/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
    showToast('Timetable schedule updated!', 'success');
    closeModal('modalEditTimetable');
    loadTimetables();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 5. Exam Edit Handlers
function openEditExamModal(id, name, batchId, subjectId, totalMark, passMark) {
  document.getElementById('editExamId').value = id;
  document.getElementById('editExamName').value = name;
  document.getElementById('editExamTotalMark').value = totalMark;
  document.getElementById('editExamPassMark').value = passMark;
  openModal('modalEditExam');
  setTimeout(() => {
    if (batchId) document.getElementById('editExamBatchSelect').value = batchId;
    if (subjectId) document.getElementById('editExamSubjectSelect').value = subjectId;
  }, 300);
}

async function handleEditExam(event) {
  event.preventDefault();
  const form = event.target;
  const id = form.id.value;
  const data = {
    exam_name: form.exam_name.value,
    batch: parseInt(form.batch_id.value),
    subject: parseInt(form.subject_id.value),
    total_mark: parseFloat(form.total_mark.value),
    pass_mark: parseFloat(form.pass_mark.value)
  };

  try {
    await apiFetch(`/academics/exams/${id}/`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
    showToast('Exam details updated!', 'success');
    closeModal('modalEditExam');
    loadExams();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 6. Fee Edit Handlers
function openEditFeeModal(id, description, amount, dueDate) {
  document.getElementById('editFeeId').value = id;
  document.getElementById('editFeeDescription').value = description;
  document.getElementById('editFeeAmount').value = amount;
  document.getElementById('editFeeDueDate').value = dueDate;
  openModal('modalEditFee');
}

async function handleEditFee(event) {
  event.preventDefault();
  const form = event.target;
  const id = form.id.value;
  const data = {
    description: form.description.value || 'Tuition Fee',
    amount: parseFloat(form.amount.value),
    due_date: form.due_date.value
  };

  try {
    await apiFetch(`/academics/fee/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
    showToast('Fee structure updated!', 'success');
    closeModal('modalEditFee');
    loadFees();
  } catch (err) {
    showToast(err.message, 'error');
  }
}
