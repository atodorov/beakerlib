%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?pyver: %define pyver %(%{__python} -c "import sys ; print sys.version[:3]")}

Name:           beaker
Version:        0.5.0
Release:        0%{?dist}
Summary:        Filesystem layout for Beaker
Group:          Applications/Internet
License:        GPLv2+
URL:            http://fedorahosted.org/beaker
Source0:        http://fedorahosted.org/releases/b/e/%{name}-%{version}.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  python-setuptools
BuildRequires:  python-setuptools-devel
BuildRequires:  python-devel
BuildRequires:  TurboGears


%package client
Summary:        Client component for talking to Beaker server
Group:          Applications/Internet
Requires:       python
Requires:       kobo-client
Requires:	python-setuptools


%package server
Summary:       Server component of Beaker
Group:          Applications/Internet
Requires:       TurboGears
Requires:       intltool
Requires:       python-decorator
Requires:       python-xmltramp
Requires:       python-ldap
Requires:       mod_wsgi
Requires:       python-tgexpandingformwidget
Requires:       httpd
Requires:       python-krbV


%package lab-controller
Summary:        Lab Controller xmlrpc server
Group:          Applications/Internet
Requires:       python
Requires:       mod_python
Requires:       httpd
Requires:       cobbler >= 1.4
Requires:       yum-utils
Requires:       /sbin/fenced
Requires:       telnet
Requires:       python-cpio

%package lib
Summary:        Test Library
Group:          QA
Obsoletes:      rhtslib
Provides:       rhtslib
Obsoletes:      beakerlib
Provides:       beakerlib

%description
Filesystem layout for beaker


%description client
This is the command line interface used to interact with the Beaker Server.


%description server
To Be Filled in - Server Side..


%description lab-controller
This is the interface to link Medusa and Cobbler together. Mostly provides
snippets and kickstarts.


%description lib
The beakerlib project means to provide a library of various helpers,
which could be used when writing Beaker tests.

%prep
%setup -q

%build
[ "$RPM_BUILD_ROOT" != "/" ] && [ -d $RPM_BUILD_ROOT ] && rm -rf $RPM_BUILD_ROOT;
DESTDIR=$RPM_BUILD_ROOT make

%install
DESTDIR=$RPM_BUILD_ROOT make install
ln -s RedHatEnterpriseLinux6.ks $RPM_BUILD_ROOT/var/lib/cobbler/kickstarts/redhat6.ks
ln -s Fedora.ks $RPM_BUILD_ROOT/var/lib/cobbler/kickstarts/Fedoradevelopment.ks

%clean
%{__rm} -rf %{buildroot}

%files server
%defattr(-,root,root,-)
%doc Server/README COPYING
%{python_sitelib}/%{name}/server/
%{python_sitelib}/%{name}.server-%{version}-*
%{python_sitelib}/%{name}.server-%{version}-py%{pyver}.egg-info/
%{_bindir}/start-%{name}
%{_bindir}/%{name}-init
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}-server.conf
%attr(-,apache,root) %{_datadir}/%{name}
%attr(-,apache,root) %config(noreplace) %{_sysconfdir}/%{name}/server.cfg
%attr(-,apache,root) %dir %{_localstatedir}/log/%{name}

%files client
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/beaker/client.conf
%{python_sitelib}/%{name}/client/
%{python_sitelib}/%{name}.client-%{version}-*
%{python_sitelib}/%{name}.client-%{version}-py%{pyver}.egg-info/
%{_bindir}/beaker-client

%files lab-controller
%defattr(-,root,root,-)
%doc LabController/README
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}-lab-controller.conf
%{_sysconfdir}/cron.daily/expire_distros
/var/lib/cobbler/triggers/sync/post/osversion.trigger
/var/lib/cobbler/snippets/*
/var/lib/cobbler/kickstarts/*
/var/www/beaker/rhts-checkin

%files lib
/usr/lib/beakerlib/*
/usr/share/beakerlib/*
/usr/share/rhts-library/*
/usr/share/man/man1/beakerlib*

%changelog
* Mon Jul 20 2009 Bill Peck <bpeck@redhat.com> - 0.4.27-0
- Expanded user_name field to 255 chars.
* Mon Jul 20 2009 Bill Peck <bpeck@redhat.com> - 0.4.26-0
- Enable ntp in cobbler snippets
* Fri Jul 17 2009 Bill Peck <bpeck@redhat.com> - 0.4.25-0
- Fixed system arch filtering to be unicode not int.
* Thu Jul 16 2009 Bill Peck <bpeck@redhat.com> - 0.4.24-0
- Allow systems to query on arch even though we are already starting
  from a distro.  This allows you to ask for systems that are not x86_64
  for example.
- Don't fail if we can't power off a system when returning it.
- Use correct username when returning a system to the pool.
- Remove --resolvedeps from RHEL6 kickstart file.
* Tue Jul 14 2009 Bill Peck <bpeck@redhat.com> - 0.4.22-0
- Fix distro_method value to be unicode instead of boolean.
* Mon Jul 13 2009 Bill Peck <bpeck@redhat.com> - 0.4.21-0
- Allow legacy RHTS to ask for distros based on install method
* Tue Jul 07 2009 Bill Peck <bpeck@redhat.com> - 0.4.20-0
- Include Workstation key for RedHatEnterpriseLinuxClient5
* Mon Jul 06 2009 Bill Peck <bpeck@redhat.com> - 0.4.19-0
- Don't populate runtest_url in ks_meta if its not defined.
* Wed Jul 01 2009 Bill Peck <bpeck@redhat.com> - 0.4.18-2
- Use RUNTEST_URL from rhts if passed.
- Include Fedoradevelopment.ks for rawhide
* Tue Jun 30 2009 Bill Peck <bpeck@redhat.com> - 0.4.17-0
- Call the correct method for _tag
* Tue Jun 30 2009 Bill Peck <bpeck@redhat.com> - 0.4.16-0
- update login_krbv method for newer kobo package
* Tue Jun 30 2009 Bill Peck <bpeck@redhat.com> - 0.4.15-0
- Call addDistros.sh from osversion.trigger if it exists.
* Mon Jun 29 2009 Bill Peck <bpeck@redhat.com> - 0.4.14-0
- Allow searching by treepath for command line client
- return distro name for legacy rhts.
* Mon Jun 22 2009 Bill Peck <bpeck@redhat.com> - 0.4.13-0
- Fixed osversion.trigger to work with methods other than nfs
* Fri Jun 19 2009 Bill Peck <bpeck@redhat.com> - 0.4.12-0
- Raise BeakerExceptions if we run into trouble
* Thu Jun 18 2009 Bill Peck <bpeck@redhat.com> - 0.4.11-0
- added install_name to distro pick method
- fixed 500 error when non-admin adds a new system with shared set.
* Fri Jun 12 2009 Bill Peck <bpeck@redhat.com> - 0.4.9-1
- releng fixed the name of rhel6 to RedHatEnterpriseLinux6 in .treeinfo
* Wed Jun 10 2009 Bill Peck <bpeck@redhat.com> - 0.4.9
- Added simple json method for tagging distros as Installable.
- Added RHEL6 kickstart file.
* Wed Jun 03 2009 Bill Peck <bpeck@redhat.com> - 0.4.8
- Catch xmlrpc errors from cobbler and record/display them
* Mon Jun 01 2009 Bill Peck <bpeck@redhat.com> - 0.4.7
- added distros list,tag,untag to beaker-client
- fixed some minor issues with the xmlrpc interface.
* Thu May 28 2009 Bill Peck <bpeck@redhat.com> - 0.4.6
- Clear systems console log via xmlrpc
* Thu May 28 2009 Bill Peck <bpeck@redhat.com> - 0.4.5
- free and available views will only show working systems now.
* Tue May 26 2009 Bill Peck <bpeck@redhat.com> - 0.4.4
- Fixed missing power_id from CSV import/export
- Use $default_password_crypted from /etc/cobbler/settings unless $password 
  is set.
* Fri May 22 2009 Bill Peck <bpeck@redhat.com> - 0.4.2
- Added in beakerlib sub package
- Fixed tempfile close in osversion.trigger
* Thu May 21 2009 Bill Peck <bpeck@redhat.com> - 0.4-3
- fix power import
* Tue May 19 2009 Bill Peck <bpeck@redhat.com> - 0.4-1
- Major reworking of directory layout.
* Tue May 12 2009 Bill Peck <bpeck@redhat.com> - 0.3-1
- First stab at client interface
