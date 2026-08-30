! Operator-side M-ANEOS query driver. Compile against libaneos.a from an
! audited M-ANEOS 1.0 tree; do not run this file inside the sandbox.
!
!   maneos-query RHO_G_CM3 TEMPERATURE_EV OUTPUT.json
!
! Reads ANEOS.INPUT from the current working directory. Reports total-material
! ANEOSV fields in CGS with temperature in eV.

program maneos_query
  implicit none
  integer :: izetl(21), mat(1), kpa(1), klst, kinp
  double precision :: temp(1), rho(1), p(1), e(1), s(1), cv(1)
  double precision :: dpdt(1), dpdr(1), fkro(1), cs(1)
  double precision :: r2pl(1), r2ph(1), zbar_out(1)
  double precision :: tev, rho_gcc
  integer :: unit_out
  character(len=256) :: output_path, arg

  common /fileos/ klst, kinp

  if (command_argument_count() /= 3) then
    write(*, '(A)') 'usage: maneos-query RHO_G_CM3 TEMPERATURE_EV OUTPUT.json'
    stop 2
  end if
  call get_command_argument(1, arg)
  read(arg, *) rho_gcc
  call get_command_argument(2, arg)
  read(arg, *) tev
  call get_command_argument(3, output_path)

  open(10, file='ANEOS.INPUT', status='old')
  open(12, file='ANEOS.INITIALIZATION.OUTPUT', status='replace')
  klst = 12
  kinp = 10
  izetl = 0
  izetl(1) = -1
  call aneos2(1, 1, 0, izetl)

  temp(1) = tev
  rho(1) = rho_gcc
  mat(1) = 1
  call aneosv(1, temp, rho, mat, p, e, s, cv, dpdt, dpdr, fkro, cs, &
       kpa, r2pl, r2ph, zbar_out)

  unit_out = 20
  open(unit_out, file=trim(output_path), status='replace')
  write(unit_out, '(A)') '{'
  write(unit_out, '(A)') '  "schema_version": "0.1.0",'
  write(unit_out, '(A)') '  "package": "m-aneos",'
  write(unit_out, '(A)') '  "model": "ANEOSV",'
  write(unit_out, '(A)') '  "units": "cgs_eV",'
  write(unit_out, '(A,ES24.16,A)') '  "density": ', rho(1), ','
  write(unit_out, '(A,ES24.16,A)') '  "temperature": ', temp(1), ','
  write(unit_out, '(A,ES24.16,A)') '  "pressure": ', p(1), ','
  write(unit_out, '(A,ES24.16,A)') '  "specific_internal_energy": ', e(1), ','
  write(unit_out, '(A,ES24.16,A)') '  "specific_entropy": ', s(1), ','
  write(unit_out, '(A,ES24.16,A)') '  "specific_heat": ', cv(1), ','
  write(unit_out, '(A,ES24.16,A)') '  "sound_speed": ', cs(1), ','
  write(unit_out, '(A,I0,A)') '  "phase": ', kpa(1), ','
  write(unit_out, '(A,ES24.16)') '  "mean_ionization": ', zbar_out(1)
  write(unit_out, '(A)') '}'
  close(unit_out)
end program maneos_query
