%global pes_events_build_date 20260919

%define dist_list almalinux centos eurolinux oraclelinux rocky cloudlinux
%define conflict_dists() %(for i in almalinux centos eurolinux oraclelinux rocky cloudlinux; do if [ "${i}" != "%{dist_name}" ]; then echo -n "leapp-data-${i} "; fi; done)

Name:		leapp-data-%{dist_name}
Version:	0.3
Release:	10%{?dist}.%{pes_events_build_date}
Summary:	data for migrating tool
Group:		Applications/Databases
License:	ASL 2.0
URL:		https://github.com/AlmaLinux/leapp-data
Source0:	leapp-data-%{version}.tar.gz
BuildArch:  noarch

BuildRequires: bc
BuildRequires: python3

%if 0%{?rhel} == 7
BuildRequires: python36-jsonschema
%endif
%if 0%{?rhel} == 8
BuildRequires: python3-jsonschema
%endif
%if 0%{?rhel} == 9
BuildRequires: python3-jsonschema
%endif

Conflicts: %{conflict_dists}

%description
%{dist_name} %{summary}


%prep
%setup -q

%build
# One command per line: rpm runs %build under sh -e, and a failing command that
# is not the last of an && list does not stop it - el7 then built and shipped the
# package with the failure. tools/tests/test_rebuild_ids.py guards it.
make DIST_VERSION=%{?rhel} all
make test

%install
make install PREFIX=%{buildroot}

%files
%doc LICENSE NOTICE README.md
%if 0%{?rhel} == 9
%{_sysconfdir}/leapp/repos.d/system_upgrade/common/files/distro/%{dist_name}/rpm-gpg/10/
%endif

%if 0%{?rhel} == 8
%{_sysconfdir}/leapp/repos.d/system_upgrade/common/files/distro/%{dist_name}/rpm-gpg/9/
%endif

%if 0%{?rhel} == 7
%{_sysconfdir}/leapp/repos.d/system_upgrade/common/files/distro/%{dist_name}/rpm-gpg/8/
%endif
%{_sysconfdir}/leapp/files/*



%changelog

* Fri Sep 18 2026 Roman Prilipskii <rprilipskii@cloudlinux.com> - 0.3-10.cloudlinux
- CLOS-7051: Add CloudLinux 9 to CloudLinux 10 upgrade data - repository map, target repositories and the AlmaLinux 10 signing key
- CLOS-7051: Rebase PES data on AlmaLinux's, which brings CloudLinux 9 to 10 package events from 193 to 2428 and picks up two years of corrections to the 7 to 8 and 8 to 9 data
- Move repository mapping data to format 1.3.0, required by leapp-repository 0.24.0, which adds a mandatory 'distro' field to every repository entry
- Advertise data stream 4.0 on every asset, which leapp-repository 0.24.0 consumes; without it the upgrade is inhibited as "outdated Leapp data assets"
- Fix the CloudLinux 7 to 8 map targeting almalinux8-ha, a repository no target repository file defines, leaving HighAvailability content unreachable
- Build vendors with no data for the target version are skipped rather than installed from files that do not exist
- CLOS-7051: Declare the ALT-ELS repositories for the CloudLinux 10 target and map cl-channel onto them; the PHP, Python, Ruby and NodeJS Selectors moved there from the main CloudLinux channel, and without them an upgrade leaves every alt-php package at its el9 build with nothing to update it from
- CLOS-7051: Map the ALT-ELS repositories on the source side too, for machines whose cloudlinux-release already pulled alt-common-release
- CLOS-7051: Suppress ten AlmaLinux package removals that CloudLinux 10 still ships and still needs - libnsl2, libwmf-lite, LibRaw, libdb, libdb-utils, enchant, libmemcached-awesome, and the LibRaw, libdb and libwmf development packages. Removing them made the el10 builds of packages that link against them uninstallable, and with allow_erasing the upgrade silently erased lve-utils, cagefs, lvemanager and lve-stats while reporting success
- CLOS-7051: Keep 23 more packages that AlmaLinux removes on CloudLinux 9 to 10 but that CloudLinux 10's alt-common repository ships and that install there: qt5-qtbase and its subpackages, the rest of libdb, double-conversion, libwmf, and the enchant and libmemcached-awesome development packages; the upgrade now carries them to their el10 builds instead of erasing them. The qt5 and qt5-devel metapackages stay removed, since nothing outside EPEL ships the qt5 modules they require for el10
- CLOS-7051: Add tools/removal_audit.py, which reports upstream removals the target still ships and a CloudLinux package still requires, so these are found before an upgrade rather than after one
- CLOS-7051: Ship the EPEL 10 signing key; vendor keys install per target version and there was no el10 source, so the target shipped no EPEL key at all
- Point the el9 and el10 target repository files at the GPG keys' per-distro location, which leapp-repository 0.24.0 moved; the el9 file means this also affected CloudLinux 8 to 9
- Check every gpgkey= in every built repository file against the build tree, so a key that moves without its references fails the build instead of a customer's upgrade

* Sun May 17 2026 Roman Prilipskii <rprilipskii@cloudlinux.com> - 0.3-9.cloudlinux
- CLOS-4056: Add CloudLinux SWNG repository entries to el8/el9 leapp upgrade and repomap data
- CLOS-2598: Add lua-cjson -> lua51-cjson mapping to PES data
- CLOS-4377: Drop legacy MariaDB package signing key block from mariadb-Server-GPG-KEY

* Sun Aug 17 2025 Oleksandr Shyshatskyi <oshyshatskyi@cloudlinux.com> - 0.3-8.cloudlinux
- CLOS-3468: Keep python3-pyOpenSSL during updates
- CLOS-3535: Keep libidn during upgrade
- CLOS-3556: Update imunify repository gpg key

* Fri Jul 11 2025 Oleksandr Shyshatskyi <oshyshatskyi@cloudlinux.com> - 0.3-7.cloudlinux
- CLOS-3457: Add alt_common repository support

* Tue Jun 10 2025 Oleksandr Shyshatskyi <oshyshatskyi@cloudlinux.com> - 0.3-6.cloudlinux
- CLOS-2988: Fix imunify360-firewall package upgrade
- CLOS-3416: Fix kmod-lve-lts installation during upgrade from CloudLinux 7 to CloudLinux 8

* Thu Feb 27 2025 Oleksandr Shyshatskyi <oshyshatskyi@cloudlinux.com> - 0.3-5.cloudlinux
- CLOS-3188: Fix kernelcare mapping for CloudLinux 8

* Mon Feb 3 2025 Oleksandr Shyshatskyi <oshyshatskyi@cloudlinux.com> - 0.3-4.cloudlinux
- CLOS-3187: Adding CloudLinux 8 to CloudLinux 9 upgrade support

* Thu Sep 26 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.3-3.cloudlinux
- Move GeoIP package if epel vendor is enabled
- Pack gpg keys inside the package to avoid "Detected unknown GPG keys" error (CLOS-2946)
- Do not use public CloudLinux repos during upgrade (CLOS-2970)

* Wed Aug 21 2024 Oleksandr Shyshatskyi <oshyshatskyi@cloudlinux.com> - 0.3-0.cloudlinux
- Rebase onto AlmaLinux

* Thu Jun 13 2024 Roman Prilipskii <rprilpskii@cloudlinux.com> - 0.2-9.cloudlinux
- Make EA4 repository optional

* Mon Feb 12 2024 Roman Prilipskii <rprilpskii@cloudlinux.com> - 0.2-8.cloudlinux
- Rebase data files on updated upstream

* Fri Jan 19 2024 Roman Prilipskii <rprilpskii@cloudlinux.com> - 0.2-7.cloudlinux
- Remove cPanel-related data from the vendor files

* Thu Dec 07 2023 Roman Prilipskii <rprilpskii@cloudlinux.com> - 0.2-6.cloudlinux
- Add CL Elevate package repository to the leapp repository map
- Add support for NGINX/MariaDB/PostgreSQL from upstream
- Add vendors.d files with EPEL support from upstream

* Mon Sep 25 2023 Roman Prilipskii <rprilpskii@cloudlinux.com> - 0.2-5.cloudlinux
- Add brotli to the PES mapping file

* Thu Jul 27 2023 Sloane Bernstein <sloane@cpanel.net>, Roman Prilipskii <rprilpskii@cloudlinux.com> - 0.2-4.cloudlinux
- Provide vendor data for WP Toolkit software
- Modify repo mapping for CL Hybrid installations

* Mon Mar 27 2023 Andrew Lukoshko <alukoshko@almalinux.org> - 0.2-3
- Add 8 to 9 migration support for Rocky Linux, EuroLinux, CentOS Stream

* Fri Sep 30 2022 Andrew Lukoshko <alukoshko@almalinux.org> - 0.2-2
- Split repomap.json

* Fri Sep 30 2022 Andrew Lukoshko <alukoshko@almalinux.org> - 0.2-1
- Add 8 to 9 migration support for AlmaLinux

* Thu Sep 1 2022 Roman Prilipskii <rprilpskii@cloudlinux.com> - 0.1-7
- made third-party files accessible for all supported distributions

* Wed Aug 17 2022 Andrew Lukoshko <alukoshko@almalinux.org> - 0.1-6
- added repomap.json file for all distributions

* Thu Mar 24 2022 Tomasz Podsiadły <tp@euro-linux.com> - 0.1-5
- Add EuroLinux to supported distributions

* Wed Mar 23 2022 Andrew Lukoshko <alukoshko@almalinux.org> - 0.1-4
- added ResilientStorage and updated repo URLs for AlmaLinux and Rocky

* Thu Oct 21 2021 Andrew Lukoshko <alukoshko@almalinux.org> - 0.1-3
- updated PES data for Oracle and Rocky

* Thu Aug 26 2021 Avi Miller <avi.miller@oracle.com> - 0.1-2
- switched to using the full oraclelinux name
- switched the Oracle Linux repos to use https
- added Apache-2.0 NOTICE attribution file

* Wed Aug 25 2021 Sergey Fokin <sfokin@almalinux.org> - 0.1-1
- initial project
