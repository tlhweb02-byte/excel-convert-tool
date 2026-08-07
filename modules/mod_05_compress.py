    else:
        zip_file = st.file_uploader(
            "📂 上传包含图片文件夹的 ZIP 压缩包",
            type=["zip"]
        )
        
        if zip_file is not None:
            if st.button("🚀 解压并深度压缩 ZIP 包内所有图片"):
                logs = []
                out_zip_buf = io.BytesIO()

                with zipfile.ZipFile(zip_file, "r") as in_zf, \
                     zipfile.ZipFile(out_zip_buf, "w", zipfile.ZIP_DEFLATED) as out_zf:

                    file_list = [
                        f for f in in_zf.namelist()
                        if not f.endswith('/')
                        and not f.startswith('__MACOSX')
                    ]

                    progress_bar = st.progress(0)

                    total_files = len(file_list)

                    for idx, inner_path in enumerate(file_list):

                        file_data = in_zf.read(inner_path)

                        filename = os.path.basename(inner_path)
                        dirname = os.path.dirname(inner_path)

                        # ✅ 修复：获取文件后缀
                        ext = os.path.splitext(filename)[1].lower()

                        if ext in ['.jpg', '.jpeg', '.png', '.webp']:

                            out_bytes, out_name, log_msg = compress_single_image(
                                file_data,
                                filename,
                                target_kb
                            )

                            # ✅ 保留原ZIP目录结构
                            if dirname:
                                out_inner_path = "/".join([
                                    "compressed_images",
                                    dirname,
                                    out_name
                                ])
                            else:
                                out_inner_path = "/".join([
                                    "compressed_images",
                                    out_name
                                ])

                            out_zf.writestr(
                                out_inner_path,
                                out_bytes
                            )

                            logs.append(log_msg)

                        else:

                            # 非图片文件保持原样
                            if dirname:
                                out_inner_path = "/".join([
                                    "compressed_images",
                                    inner_path
                                ])
                            else:
                                out_inner_path = "/".join([
                                    "compressed_images",
                                    filename
                                ])

                            out_zf.writestr(
                                out_inner_path,
                                file_data
                            )

                            logs.append(
                                f"⏩ [原样复制非图片] {filename}"
                            )


                        progress_bar.progress(
                            (idx + 1) / total_files
                        )


                out_zip_buf.seek(0)

                st.success(
                    "🎉 ZIP 压缩包处理完成！已保持原嵌套目录结构。"
                )

                st.subheader("📝 处理日志监控")

                st.code(
                    "\n".join(logs),
                    language="text"
                )


                st.download_button(
                    label="📥 一键下载精压缩后的 ZIP 压缩包",
                    data=out_zip_buf,
                    file_name="compressed_folder.zip",
                    mime="application/zip"
                )
