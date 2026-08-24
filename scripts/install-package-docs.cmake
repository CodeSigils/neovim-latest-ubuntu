# Add Debian package documentation that upstream Neovim's cross-platform
# CPack configuration intentionally does not install.

foreach(required_env NEOVIM_SOURCE_DIR NEOVIM_PACKAGE_VERSION PACKAGE_CHANGELOG_DATE)
  if("$ENV{${required_env}}" STREQUAL "")
    message(FATAL_ERROR "${required_env} is required")
  endif()
endforeach()

# CPack exposes its staging root through DESTDIR. Neovim's generated CPack
# configuration retains /usr/local as CMAKE_INSTALL_PREFIX even though the DEB
# payload is rooted at /usr, so use Debian's policy-defined documentation path.
if("$ENV{DESTDIR}" STREQUAL "")
  message(FATAL_ERROR "DESTDIR is required when staging package documentation")
endif()
set(documentation_dir "$ENV{DESTDIR}/usr/share/doc/neovim")
file(MAKE_DIRECTORY "${documentation_dir}")
file(COPY_FILE
  "$ENV{NEOVIM_SOURCE_DIR}/LICENSE.txt"
  "${documentation_dir}/copyright"
  ONLY_IF_DIFFERENT
)

set(changelog "neovim ($ENV{NEOVIM_PACKAGE_VERSION}) unstable; urgency=medium\n\n")
string(APPEND changelog "  * Package upstream Neovim for Ubuntu.\n\n")
string(APPEND changelog
  " -- CodeSigils <codesigils@users.noreply.github.com>  $ENV{PACKAGE_CHANGELOG_DATE}\n"
)
file(WRITE "${documentation_dir}/changelog" "${changelog}")
execute_process(
  COMMAND gzip -9 -n "${documentation_dir}/changelog"
  COMMAND_ERROR_IS_FATAL ANY
)
