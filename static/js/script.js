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

        // 邮箱设置 - 修改这里！！！
        const emailSettingsForm = document.getElementById('emailSettingsForm');
        if (emailSettingsForm) {
            emailSettingsForm.addEventListener('submit', function(e) {
                e.preventDefault();

                const email = document.getElementById('email').value.trim();

                // 创建FormData对象而不是JSON
                const formData = new FormData();
                formData.append('email', email);

                // 添加CSRF令牌作为表单字段（某些Flask配置可能需要这个）
                formData.append('csrf_token', getCSRFToken());

                fetch('/admin/settings/email', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCSRFToken()  // 保持请求头中的CSRF
                        // 注意：不要设置Content-Type，让浏览器自动设置multipart/form-data
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
                        showResult('emailSettingsResult', `更新失败: ${Array.isArray(data.details) ? data.details.join(', ') : data.error}`, false, 5000);
                    } else {
                        showResult('emailSettingsResult', data.message, true, 5000);
                    }
                })
                .catch(error => {
                    let errorMessage = '更新失败，请重试';
                    if (error && error.error) {
                        errorMessage = error.error;
                    } else if (error.message) {
                        errorMessage = error.message;
                    }
                    showResult('emailSettingsResult', errorMessage, false, 5000);
                    console.error('Email Settings Error:', error);
                });
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