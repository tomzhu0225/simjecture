"""Study entry point; all solver and data-transfer sources are explicit inputs."""
import sys
if sys.argv[1] == 'flash':
    import flash_driver
    sys.argv.pop(1)
    raise SystemExit(flash_driver.main())
if sys.argv[1] == 'pic':
    import kinetic
    sys.argv.pop(1)
    kinetic.cli()
elif sys.argv[1] == 'select':
    import select_patch
    sys.argv.pop(1)
    select_patch.main()
else:
    raise ValueError('Unknown operation')
