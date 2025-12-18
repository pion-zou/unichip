// 前台页面脚本
document.addEventListener('DOMContentLoaded', function() {
    // 获取CSRF令牌的辅助函数
    function getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        console.warn('CSRF token meta tag not found! This might cause issues with POST requests.');
        return '';
    }

    // 搜索功能
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const modelInput = document.getElementById('model');
            const model = modelInput.value.trim();

            if (!model) {
                showResult('resultError', '请输入芯片型号', false, 5000);
                modelInput.focus();
                return;
            }

            // 显示加载状态
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 查询中...';
            submitBtn.disabled = true;

            // 准备请求数据
            const formData = new FormData();
            formData.append('model', model);

            fetch('/search', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken()  // 添加CSRF令牌
                    // 注意：不设置Content-Type，让浏览器自动设置正确的边界
                },
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw err;
                    }).catch(() => {
                        throw {error: `服务器错误: ${response.status} ${response.statusText}`};
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    showResult('resultError', data.error, false, 5000);
                    document.getElementById('chipDetails').style.display = 'none';
                } else {
                    // 安全处理可能为null的字段
                    document.getElementById('chipModel').textContent = data.model || 'N/A';
                    document.getElementById('chipDescription').textContent = data.description || '无描述';

                    // 显示库存状态（改进零库存显示）
                    const stock = data.stock !== null && data.stock !== undefined ? data.stock : 0;
                    document.getElementById('chipStock').textContent = stock;

                    // 显示库存状态提示
                    const stockStatus = document.getElementById('stockStatus');
                    if (stockStatus) {
                        if (stock > 10) {
                            stockStatus.innerHTML = '<span class="badge bg-success">充足</span>';
                        } else if (stock > 0) {
                            stockStatus.innerHTML = '<span class="badge bg-warning text-dark">少量</span>';
                        } else {
                            stockStatus.innerHTML = '<span class="badge bg-danger">缺货</span>';
                        }
                    }

                    // 安全处理价格
                    const price = data.price !== null && data.price !== undefined ? data.price : 0;
                    document.getElementById('chipPrice').textContent = price > 0 ? `¥${price.toFixed(2)}` : '价格面议';

                    showResult('resultSuccess', '查询成功', true, 10000); // 延长显示时间
                    document.getElementById('chipDetails').style.display = 'block';
                }
                document.getElementById('searchResult').style.display = 'block';
            })
            .catch(error => {
                let errorMessage = '查询失败，请重试';
                if (error && error.error) {
                    errorMessage = error.error;
                } else if (error.message) {
                    errorMessage = error.message;
                } else if (typeof error === 'string') {
                    errorMessage = error;
                }
                showResult('resultError', errorMessage, false, 5000);
                console.error('Search Error:', error);
            })
            .finally(() => {
                // 恢复按钮状态
                submitBtn.innerHTML = originalBtnText;
                submitBtn.disabled = false;
            });
        });
    }

    // 联系表单
    const contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(contactForm);
            const data = {};
            for (const [key, value] of formData.entries()) {
                data[key] = value;
            }

            fetch('/contact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showResult('contactResult', `提交失败: ${Array.isArray(data.details) ? data.details.join(', ') : data.error}`, false, 5000);
                } else {
                    showResult('contactResult', data.message, true, 5000);
                    contactForm.reset();
                }
            })
            .catch(error => {
                showResult('contactResult', '提交失败，请重试', false, 5000);
                console.error('Error:', error);
            });
        });
    }

    // "需要更多？立即咨询"按钮
    const inquireBtn = document.getElementById('inquireBtn');
    if (inquireBtn) {
        inquireBtn.addEventListener('click', function() {
            document.getElementById('contact').scrollIntoView({ behavior: 'smooth' });
            // 自动填充型号
            const model = document.getElementById('chipModel').textContent;
            if (model && model !== 'N/A') {
                document.getElementById('message').value = `我对型号 ${model} 感兴趣，请提供详细报价和交货时间。`;
            }
        });
    }

    // 后台管理功能
    if (document.getElementById('addChipForm')) {
        // 添加芯片
        document.getElementById('saveChipBtn').addEventListener('click', function() {
            const formData = {
                model: document.getElementById('addModel').value,
                description: document.getElementById('addDescription').value,
                stock: parseInt(document.getElementById('addStock').value),
                price: parseFloat(document.getElementById('addPrice').value)
            };

            fetch('/admin/chip/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showResult('addChipResult', `添加失败: ${Array.isArray(data.details) ? data.details.join(', ') : data.error}`, false, 5000);
                } else {
                    showResult('addChipResult', data.message, true, 1500);
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                }
            })
            .catch(error => {
                showResult('addChipResult', '添加失败，请重试', false, 5000);
                console.error('Error:', error);
            });
        });

        // 编辑芯片
        document.querySelectorAll('.edit-chip').forEach(button => {
            button.addEventListener('click', function() {
                const id = this.getAttribute('data-id');
                fetch(`/admin/chip/${id}`)
                .then(response => response.json())
                .then(chip => {
                    document.getElementById('editId').value = chip.id;
                    document.getElementById('editModel').value = chip.model;
                    document.getElementById('editDescription').value = chip.description;
                    document.getElementById('editStock').value = chip.stock;
                    document.getElementById('editPrice').value = chip.price;
                    const editModal = new bootstrap.Modal(document.getElementById('editChipModal'));
                    editModal.show();
                })
                .catch(error => {
                    alert('获取芯片信息失败');
                    console.error('Error:', error);
                });
            });
        });

        // 更新芯片
        document.getElementById('updateChipBtn').addEventListener('click', function() {
            const formData = {
                model: document.getElementById('editModel').value,
                description: document.getElementById('editDescription').value,
                stock: parseInt(document.getElementById('editStock').value),
                price: parseFloat(document.getElementById('editPrice').value)
            };

            const id = document.getElementById('editId').value;
            fetch(`/admin/chip/update/${id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showResult('editChipResult', `更新失败: ${Array.isArray(data.details) ? data.details.join(', ') : data.error}`, false, 5000);
                } else {
                    showResult('editChipResult', data.message, true, 1500);
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                }
            })
            .catch(error => {
                showResult('editChipResult', '更新失败，请重试', false, 5000);
                console.error('Error:', error);
            });
        });

        // 删除芯片
        document.querySelectorAll('.delete-chip').forEach(button => {
            button.addEventListener('click', function() {
                if (!confirm('确定要删除这个芯片吗？')) {
                    return;
                }

                const id = this.getAttribute('data-id');
                fetch(`/admin/chip/delete/${id}`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCSRFToken()
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.message) {
                        alert(data.message);
                        document.getElementById(`chip-${id}`).remove();
                    }
                })
                .catch(error => {
                    alert('删除失败，请重试');
                    console.error('Error:', error);
                });
            });
        });

        // ============ 抄送邮箱管理功能 ============

        // 加载抄送邮箱列表
        loadCCEmails();

        // 添加抄送邮箱表单提交
        const addCCEmailForm = document.getElementById('addCCEmailForm');
        if (addCCEmailForm) {
            addCCEmailForm.addEventListener('submit', function(e) {
                e.preventDefault();
                addCCEmail();
            });
        }

        // 邮箱设置表单提交（批量添加抄送邮箱）
        const emailSettingsForm = document.getElementById('emailSettingsForm');
        if (emailSettingsForm) {
            emailSettingsForm.addEventListener('submit', function(e) {
                e.preventDefault();
                updateEmailSettings();
            });
        }

        // 加载抄送邮箱列表
        function loadCCEmails() {
            fetch('/admin/email/cc', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应异常');
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    console.error('加载抄送邮箱失败:', data.error);
                    showCCMessage('加载抄送邮箱失败', false);
                } else if (data.cc_emails) {
                    renderCCEmailList(data.cc_emails);
                }
            })
            .catch(error => {
                console.error('加载抄送邮箱失败:', error);
                showCCMessage('加载抄送邮箱失败，请刷新重试', false);
            });
        }

        // 渲染抄送邮箱列表
        function renderCCEmailList(ccEmails) {
            const tableBody = document.getElementById('ccEmailTableBody');
            if (!tableBody) return;

            if (!ccEmails || ccEmails.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center text-muted">暂无抄送邮箱</td>
                    </tr>
                `;
                return;
            }

            tableBody.innerHTML = ccEmails.map(cc => `
                <tr id="cc-email-${cc.id}">
                    <td>${cc.email}</td>
                    <td>
                        <span class="badge ${cc.is_active ? 'bg-success' : 'bg-secondary'}">
                            ${cc.is_active ? '激活' : '停用'}
                        </span>
                    </td>
                    <td>${cc.created_at ? new Date(cc.created_at).toLocaleDateString() : '-'}</td>
                    <td>
                        <button class="btn btn-sm ${cc.is_active ? 'btn-warning' : 'btn-success'} btn-toggle-cc" 
                                data-id="${cc.id}" data-active="${cc.is_active}">
                            ${cc.is_active ? '停用' : '激活'}
                        </button>
                        <button class="btn btn-sm btn-danger btn-delete-cc" data-id="${cc.id}">
                            删除
                        </button>
                    </td>
                </tr>
            `).join('');

            // 绑定按钮事件
            bindCCEmailEvents();
        }

        // 绑定抄送邮箱按钮事件
        function bindCCEmailEvents() {
            // 切换状态按钮
            document.querySelectorAll('.btn-toggle-cc').forEach(btn => {
                btn.addEventListener('click', function() {
                    const id = this.getAttribute('data-id');
                    const currentActive = this.getAttribute('data-active') === 'true';
                    toggleCCEmail(id, currentActive);
                });
            });

            // 删除按钮
            document.querySelectorAll('.btn-delete-cc').forEach(btn => {
                btn.addEventListener('click', function() {
                    const id = this.getAttribute('data-id');
                    if (confirm('确定要删除这个抄送邮箱吗？')) {
                        deleteCCEmail(id);
                    }
                });
            });
        }

        // 添加抄送邮箱
        function addCCEmail() {
            const emailInput = document.getElementById('ccEmail');
            const email = emailInput.value.trim();

            if (!email) {
                showCCMessage('请输入有效的邮箱地址', false);
                return;
            }

            // 简单的邮箱格式验证
            if (!validateEmail(email)) {
                showCCMessage('请输入有效的邮箱格式', false);
                return;
            }

            fetch('/admin/email/cc', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ email: email })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw err;
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.message) {
                    showCCMessage(data.message, true);
                    emailInput.value = '';
                    loadCCEmails();
                } else if (data.error) {
                    showCCMessage(data.error, false);
                }
            })
            .catch(error => {
                let errorMessage = '添加失败，请重试';
                if (error && error.error) {
                    errorMessage = error.error;
                }
                showCCMessage(errorMessage, false);
                console.error('添加抄送邮箱失败:', error);
            });
        }

        // 切换抄送邮箱状态
        function toggleCCEmail(id, currentStatus) {
            fetch(`/admin/email/cc/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ is_active: !currentStatus })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw err;
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.message) {
                    showCCMessage(data.message, true);
                    loadCCEmails();
                } else if (data.error) {
                    showCCMessage(data.error, false);
                }
            })
            .catch(error => {
                let errorMessage = '操作失败，请重试';
                if (error && error.error) {
                    errorMessage = error.error;
                }
                showCCMessage(errorMessage, false);
                console.error('切换状态失败:', error);
            });
        }

        // 删除抄送邮箱
        function deleteCCEmail(id) {
            fetch(`/admin/email/cc/${id}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw err;
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.message) {
                    showCCMessage(data.message, true);
                    loadCCEmails();
                } else if (data.error) {
                    showCCMessage(data.error, false);
                }
            })
            .catch(error => {
                let errorMessage = '删除失败，请重试';
                if (error && error.error) {
                    errorMessage = error.error;
                }
                showCCMessage(errorMessage, false);
                console.error('删除抄送邮箱失败:', error);
            });
        }

        // 显示抄送邮箱消息
        function showCCMessage(message, isSuccess) {
            const messageDiv = document.getElementById('ccEmailMessage');
            if (messageDiv) {
                messageDiv.style.display = 'block';
                messageDiv.className = isSuccess ? 'alert alert-success' : 'alert alert-danger';
                messageDiv.innerHTML = message;

                // 3秒后自动隐藏
                setTimeout(() => {
                    messageDiv.style.display = 'none';
                }, 3000);
            } else {
                // 如果没有消息div，使用alert
                alert(message);
            }
        }

        // 邮箱格式验证
        function validateEmail(email) {
            const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return re.test(email);
        }

        // 邮箱设置表单提交（批量添加抄送邮箱）
        function updateEmailSettings() {
            const emailInput = document.getElementById('email');
            const email = emailInput.value.trim();

            if (!email) {
                showResult('emailSettingsResult', '请输入邮箱地址', false, 5000);
                return;
            }

            // 创建FormData对象
            const formData = new FormData();
            formData.append('email', email);

            // 检查是否有批量抄送邮箱输入
            const batchCCInput = document.getElementById('batchCCEmails');
            if (batchCCInput && batchCCInput.value.trim()) {
                formData.append('cc_email', batchCCInput.value.trim());
            }

            fetch('/admin/settings/email', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw err;
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    showResult('emailSettingsResult', `更新失败: ${Array.isArray(data.details) ? data.details.join(', ') : data.error}`, false, 5000);
                } else {
                    showResult('emailSettingsResult', data.message, true, 5000);
                    // 如果有批量添加抄送邮箱，重新加载列表
                    if (batchCCInput && batchCCInput.value.trim()) {
                        loadCCEmails();
                        batchCCInput.value = '';
                    }
                }
            })
            .catch(error => {
                let errorMessage = '更新失败，请重试';
                if (error && error.error) {
                    errorMessage = error.error;
                }
                showResult('emailSettingsResult', errorMessage, false, 5000);
                console.error('Email Settings Error:', error);
            });
        }

        // 邮箱设置表单提交（批量添加抄送邮箱）
        function updateEmailSettings() {
            const emailInput = document.getElementById('email');
            const email = emailInput.value.trim();

            if (!email) {
                showResult('emailSettingsResult', '请输入邮箱地址', false, 5000);
                return;
            }

            // 创建FormData对象
            const formData = new FormData();
            formData.append('email', email);

            // 检查是否有批量抄送邮箱输入
            const batchCCInput = document.getElementById('batchCCEmails');
            if (batchCCInput && batchCCInput.value.trim()) {
                formData.append('cc_email', batchCCInput.value.trim());
            }

            fetch('/admin/settings/email', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw err;
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    showResult('emailSettingsResult', `更新失败: ${Array.isArray(data.details) ? data.details.join(', ') : data.error}`, false, 5000);
                } else {
                    showResult('emailSettingsResult', data.message, true, 5000);
                    // 如果有批量添加抄送邮箱，重新加载列表
                    if (batchCCInput && batchCCInput.value.trim()) {
                        loadCCEmails();
                        batchCCInput.value = '';
                    }
                }
            })
            .catch(error => {
                let errorMessage = '更新失败，请重试';
                if (error && error.error) {
                    errorMessage = error.error;
                }
                showResult('emailSettingsResult', errorMessage, false, 5000);
                console.error('Email Settings Error:', error);
            });
        }
    }

    // 显示结果消息
    function showResult(elementId, message, isSuccess, duration = 5000) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error(`Element with id '${elementId}' not found!`);
            return;
        }

        element.innerHTML = message;
        element.className = isSuccess ? 'alert alert-success' : 'alert alert-danger';
        element.style.display = 'block';

        // 如果duration为0，则不自动隐藏
        if (duration > 0) {
            // 隐藏之前的定时器（避免重复触发）
            if (element.hideTimeout) {
                clearTimeout(element.hideTimeout);
            }

            // 设置新的定时器
            element.hideTimeout = setTimeout(() => {
                element.style.display = 'none';
                element.hideTimeout = null;
            }, duration);
        }
    }
});